#-----------------------------------------------------------------------------
# Copyright (c) 2025, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

# NOTE: CPython does not, in fact, guarantee reproducibility of byte-compiled .pyc modules - see [1, 2, 3].
#
# In our case, the lack of .pyc reproducibility creeps up when trying to byte-compile the same module multiple times
# *within the same python process*; the byte-compiled result of the very first attempt will differ from that of the
# second attempt, while result of all subsequent attempts will be the same as the second attempt. Note that this does
# not affect regular PyInstaller use (because each build is ran as a different process, so unless multiple targets are
# built in the same .spec file, each module is byte-compiled at most once) as much as it does our test suite (where
# multiple builds are executed within the context of the same `pytest` runner).
#
# The issues stemming from the non-deterministic behavior of FLAG_REF tracking can be, to some extent, mitigated by
# post-processing the byte-code using `marshalparser` tool [4]. However, this comes at performance cost that makes it
# unsuitable for the amount of processing done as part of our test suite. Furthermore, it does not seem to fully
# mitigate the behavior in python >= 3.13, where additional non-reproducibility aspects were introduced by interning
# of co_filename, co_name, and co_qualname [5].
#
# Therefore, to allow us to test at least some aspects of reproducibility, the tests in this file that perform multiple
# subsequent build runs and compare results between them first perform a throw-away "calibration" build and ignore its
# results. This should hopefully ensure reproducibility of the byte-compiled python code in subsequent, real build runs,
# and ensure that tests work as expected regardless of the order in which they are executed (or when executed on their
# own).
#
# References:
# [1] https://github.com/astral-sh/uv/issues/10619
# [2] https://github.com/python/cpython/issues/129724
# [3] https://github.com/python/cpython/issues/78274
# [4] https://pypi.org/project/marshalparser
# [5] https://github.com/python/cpython/commit/2ba2c142a615abbd8138d253edfe02426c386961

import dataclasses
import filecmp
import time

import pytest

from PyInstaller import compat


def test_reproducible_subsequent_builds(pyi_builder, tmp_path, monkeypatch):
    from PyInstaller.archive.readers import CArchiveReader

    # On GHA ubuntu runners, we seem to be getting occasional test failure due to differences in collected modules'
    # bytecode, in spite of the "calibration" step below. This seems to affect python < 3.11 on all platforms; most
    # often, it fails on linux with 3.9, but 3.8 and 3.10 have also been observed to fail. Since the lack of .pyc
    # bytecode reproducibility seems to be out of our control, xfail the test.
    if not compat.is_py311:
        pytest.xfail("Issues with reproducibility of collected modules' bytecode.")

    # On Windows, we need to set SOURCE_DATE_EPOCH for the build to be fully reproducible (i.e., the build timestamp
    # that is embedded in the executable)
    if compat.is_win:
        monkeypatch.setenv('SOURCE_DATE_EPOCH', f"{time.time():.0f}")

    # Two consecutive builds (preceded by a throw-away "calibration" one, as per note at the top of this file); ensure
    # their build and dist dirs are different.
    pyi_builder._dist_dir = tmp_path / 'dist-0'
    pyi_builder._build_dir = tmp_path / 'build-0'
    pyi_builder.test_script('pyi_helloworld.py')

    pyi_builder._dist_dir = tmp_path / 'dist-1'
    pyi_builder._build_dir = tmp_path / 'build-1'
    pyi_builder.test_script('pyi_helloworld.py')
    executable1 = pyi_builder._find_executables("pyi_helloworld")[0]
    print("First executable:", executable1)

    pyi_builder._dist_dir = tmp_path / 'dist-2'
    pyi_builder._build_dir = tmp_path / 'build-2'
    pyi_builder.test_script('pyi_helloworld.py')
    executable2 = pyi_builder._find_executables("pyi_helloworld")[0]
    print("Second executable:", executable2)

    pkg1 = CArchiveReader(executable1)
    pkg2 = CArchiveReader(executable2)

    # First, compare TOCs of embedded PYZ archives - so we can get detailed error if their elements differ.
    def _find_pyz(pkg):
        pyz = [name for name, (*_, typecode) in pkg.toc.items() if typecode == 'z']
        return pyz[0]

    pyz1_name = _find_pyz(pkg1)
    pyz1 = pkg1.open_embedded_archive(pyz1_name)

    pyz2_name = _find_pyz(pkg2)
    pyz2 = pkg2.open_embedded_archive(pyz2_name)

    assert pyz1.toc == pyz2.toc

    # Compare PYZ archives bit-by-bit
    pyz1_data = pkg1.extract(pyz1_name)
    pyz2_data = pkg2.extract(pyz2_name)

    assert pyz1_data == pyz2_data

    # Compare PKG TOCs
    assert pkg1.toc == pkg2.toc
    assert pkg1.options == pkg2.options

    # Compare PKG archives bit-by-bit
    pkg1_data = pkg1.raw_pkg_data()
    pkg2_data = pkg2.raw_pkg_data()

    assert pkg1_data == pkg2_data

    # Compare whole executables
    assert filecmp.cmp(executable1, executable2, shallow=False)


# Test that in macOS executables, Mach-O image UUIDs are modified during the build process, based on the contents (hash)
# of the PKG archive.
@pytest.mark.darwin
def test_macos_executable_uuid(pyi_builder_spec, tmp_path):
    # Helper for reading Mach-O image UUIDs from executable.
    def _read_uuids(filename):
        import uuid

        from macholib.mach_o import LC_UUID
        from macholib.MachO import MachO

        uuids = []

        executable = MachO(filename)
        for header in executable.headers:
            # Find LC_UUID command
            uuid_cmd = [cmd for cmd in header.commands if cmd[0].cmd == LC_UUID]
            if not uuid_cmd:
                continue
            uuid_cmd = uuid_cmd[0]

            # Copy UUID
            uuids.append(uuid.UUID(bytes=uuid_cmd[1].uuid))

        return uuids

    # Helper structure for organizing the results of build runs.
    @dataclasses.dataclass
    class Result:
        # For each resulting executable, we store  the list of UUIDs extracted from all available arch slices.
        program1_onedir: list
        program1_onefile: list
        program1_onedir_w: list
        program1_onedir_w_app: list

        program2_onedir: list
        program2_onefile: list

        program3_onedir: list
        program3_onefile: list

        @staticmethod
        def create_result(dist_path):
            return Result(
                # First program
                program1_onedir=_read_uuids(dist_path / "program1_onedir/program1_onedir"),
                program1_onefile=_read_uuids(dist_path / "program1_onefile"),
                program1_onedir_w=_read_uuids(dist_path / "program1_onedir_w/program1_onedir_w"),
                program1_onedir_w_app=_read_uuids(dist_path / "program1_onedir_w.app/Contents/MacOS/program1_onedir_w"),
                # Second program
                program2_onedir=_read_uuids(dist_path / "program2_onedir/program2_onedir"),
                program2_onefile=_read_uuids(dist_path / "program2_onefile"),
                # Third program
                program3_onedir=_read_uuids(dist_path / "program3_onedir/program3_onedir"),
                program3_onefile=_read_uuids(dist_path / "program3_onefile"),
            )

        def display_result(self, build_name):
            print(f"{build_name}")

            print("* program1_onedir:", self.program1_onedir)
            print("* program1_onefile:", self.program1_onefile)
            print("* program1_onedir_w:", self.program1_onedir_w)
            print("* program1_onedir_w_app:", self.program1_onedir_w_app)

            print("* program2_onedir:", self.program2_onedir)
            print("* program2_onedfile:", self.program2_onefile)

            print("* program3_onedir:", self.program3_onedir)
            print("* program3_onefile:", self.program3_onefile)

    # Build the test programs - throw-away "calibration" build, as per note at the top of this file.
    pyi_builder_spec._dist_dir = tmp_path / 'dist-0'
    pyi_builder_spec._build_dir = tmp_path / 'build-0'
    pyi_builder_spec.test_spec(
        'pyi_macos_executable_uuid.spec',
        # Provide name of one application to appease the find/run-executable phase.
        app_name='program1_onedir',
    )

    # Build the test programs - first run.
    pyi_builder_spec._dist_dir = tmp_path / 'dist-1'
    pyi_builder_spec._build_dir = tmp_path / 'build-1'
    pyi_builder_spec.test_spec(
        'pyi_macos_executable_uuid.spec',
        app_name='program1_onedir',
    )

    result1 = Result.create_result(pyi_builder_spec._dist_dir)
    result1.display_result("First build")

    # onefile and onedir have different contents of PKG archive.
    assert result1.program1_onedir != result1.program1_onefile

    # windowed mode uses different bootloader executable.
    assert result1.program1_onedir != result1.program1_onedir_w

    # In windowed mode, regular onedir build uses same executable as the .app bundle. So this test is technically a
    # no-op, unless we try to ensure that .app bundle codepath doesn't additionally reset the UUIDs in some way.
    assert result1.program1_onedir_w == result1.program1_onedir_w_app

    # program2 is built using the same script as program1.
    assert result1.program2_onedir == result1.program1_onedir
    assert result1.program2_onefile == result1.program1_onefile

    # program3 is built using different script.
    assert result1.program3_onedir != result1.program1_onedir
    assert result1.program3_onefile != result1.program1_onefile

    # Build the test programs - second run.
    pyi_builder_spec._dist_dir = tmp_path / 'dist-2'
    pyi_builder_spec._build_dir = tmp_path / 'build-2'
    pyi_builder_spec.test_spec(
        'pyi_macos_executable_uuid.spec',
        app_name='program1_onedir',
    )

    result2 = Result.create_result(pyi_builder_spec._dist_dir)
    result2.display_result("Second build")

    # Compare both results - the UUIDs should be identical across all pairs of corresponding programs.
    assert result1 == result2
