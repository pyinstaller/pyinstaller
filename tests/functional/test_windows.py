#-----------------------------------------------------------------------------
# Copyright (c) 2005-2026, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""Windows-specific functional tests."""

import os
import pathlib
import sys

import pytest


@pytest.mark.win32
def test_renamed_exe(pyi_builder):
    _old_find_executables = pyi_builder._find_executables

    def _find_executables(name):
        old_executables = _old_find_executables(name)
        new_executables = []
        for old_exe in old_executables:
            old_exe_path = pathlib.Path(old_exe)
            new_exe_path = old_exe_path.with_name(f"renamed_{old_exe_path.name}")
            old_exe_path.rename(new_exe_path)

            new_executables.append(str(new_exe_path))
        return new_executables

    pyi_builder._find_executables = _find_executables
    pyi_builder.test_source("print('Hello Python!')")


@pytest.mark.win32
def test_pe_checksum(pyi_builder):
    import ctypes
    from ctypes import wintypes

    pyi_builder.test_source("print('hello')")
    exes = pyi_builder._find_executables('test_source')
    assert exes
    for exe in exes:
        # Validate the PE checksum using the official Windows API for doing so.
        # https://docs.microsoft.com/en-us/windows/win32/api/imagehlp/nf-imagehlp-mapfileandchecksumw
        header_sum = wintypes.DWORD()
        checksum = wintypes.DWORD()
        assert ctypes.windll.imagehlp.MapFileAndCheckSumW(
            ctypes.c_wchar_p(exe), ctypes.byref(header_sum), ctypes.byref(checksum)
        ) == 0

        assert header_sum.value == checksum.value


@pytest.mark.win32
@pytest.mark.parametrize("icon", ["icon_default", "icon_none", "icon_given"])
def test_application_executable_has_manifest(pyi_builder, icon):
    """
    Verify that builds on Windows end up having manifest embedded. See issue #5624.
    This test was initially limited only to onefile builds, but as we now always embed manifest into executable, it
    now covers both builds.
    """
    from PyInstaller.utils.win32 import winmanifest
    from PyInstaller import PACKAGEPATH

    # Icon type
    if icon == 'icon_default':
        # Default; no --icon argument
        extra_args = []
    elif icon == 'icon_none':
        # Disable icon completely; --icon NONE
        extra_args = ['--icon', 'NONE']
    elif icon == 'icon_given':
        # Locate pyinstaller's default icon, and explicitly give it
        # via --icon argument
        icon_path = os.path.join(PACKAGEPATH, 'bootloader', 'images', 'icon-console.ico')
        extra_args = ['--icon', icon_path]
    # Build the executable...
    pyi_builder.test_source("""print('Hello world!')""", pyi_args=extra_args)
    # ... and ensure that it contains manifest
    exes = pyi_builder._find_executables('test_source')
    assert exes
    for exe in exes:
        manifest = winmanifest.read_manifest_from_executable(exe)
        assert manifest, "No manifest resources found!"


@pytest.mark.win32
def test_standard_streams_in_windowed_mode(pyi_builder, tmp_path):
    # NOTE: this is windowed/noconsole win32 test, and unhandled exceptions bring up unhandled exception dialog, which
    # blocks the test until the timeout. Therefore, exception messages are recorded in a text file, which allows us to
    # fail the test with a detailed error message.
    error_file = tmp_path / 'error.txt'

    pyi_builder.test_source(
        """
        import sys

        try:
            # In a windowed/noconsole build, all streams should be None.
            # With contemporary PyInstaller versions, this applies to both underscored and "regular" variables.
            assert sys.__stdin__ is None, f"sys.__stdin__ is not None: {sys.__stdin__}"
            assert sys.__stdout__ is None, f"sys.__stdout__ is not None: {sys.__stdout__}"
            assert sys.__stderr__ is None, f"sys.__stderr__ is not None: {sys.__stderr__}"

            assert sys.stdin is None, f"sys.stdin is not None: {sys.stdin}"
            assert sys.stdout is None, f"sys.stdout is not None: {sys.stdout}"
            assert sys.stderr is None, f"sys.stderr is not None: {sys.stderr}"
        except Exception as e:
            try:
                error_file = sys.argv[1]
                with open(error_file, "w", encoding="utf-8") as fp:
                    import traceback
                    fp.write(traceback.format_exc())
            except Exception:
                sys.exit(1)
        """,
        pyi_args=['--windowed'],
        app_args=[str(error_file)],
    )

    if error_file.is_file():
        error_text = error_file.read_text(encoding='utf-8')
        pytest.fail(f"Test program wrote error file (see below)!\n{error_text}")


@pytest.mark.win32
def test_subprocess_in_windowed_mode(pyi_builder, tmp_path):
    """Test invoking subprocesses from a PyInstaller app built in windowed mode."""

    # See comment in the `test_standard_streams_in_windowed_mode` above.
    error_file = tmp_path / 'error.txt'

    pyi_builder.test_source(
        r"""
        import sys

        try:
            from subprocess import PIPE, run
            from unittest import TestCase

            # Lazily use unittest's rich assertEqual() for assertions with builtin diagnostics.
            assert_equal = TestCase().assertEqual

            # Path to python interpreter, passed as first argument.
            python = sys.argv[1]

            # Run with empty command to ensure interpreter works.
            run([python, "-c", ""], check=True)

            # Verify that stdin, stdout and stderr still work and haven't been muddled.
            p = run([python, "-c", "print('foo')"], stdout=PIPE, encoding='utf-8')
            assert_equal(p.stdout, "foo\n", p.stdout)

            p = run([python, "-c", r"import sys; sys.stderr.write('bar\n')"], stderr=PIPE, encoding='utf-8')
            assert_equal(p.stderr, "bar\n", p.stderr)

            p = run([python], input="print('foo')\nprint('bar')\n", stdout=PIPE, encoding='utf-8')
            assert_equal(p.stdout, "foo\nbar\n", p.stdout)
        except Exception as e:
            try:
                error_file = sys.argv[2]
                with open(error_file, "w", encoding="utf-8") as fp:
                    import traceback
                    fp.write(traceback.format_exc())
            except Exception:
                sys.exit(1)
        """,
        pyi_args=["--windowed"],
        app_args=[str(sys.executable), str(error_file)],
    )

    if error_file.is_file():
        error_text = error_file.read_text(encoding='utf-8')
        pytest.fail(f"Test program wrote error file (see below)!\n{error_text}")
