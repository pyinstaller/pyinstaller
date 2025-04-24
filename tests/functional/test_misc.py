#-----------------------------------------------------------------------------
# Copyright (c) 2021-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import os
import pathlib
import sys
import json

import pytest

from PyInstaller import compat
from PyInstaller.utils.tests import onefile_only

# Directory with testing modules used in some tests.
_MODULES_DIR = pathlib.Path(__file__).parent / 'modules'


# Test that in python 3.11 and later, sys._stdlib_dir is set and that python-frozen modules have __file__ attribute.
@pytest.mark.skipif(not compat.is_py311, reason="applicable only to python >= 3.11")
def test_frozen_stdlib_modules(pyi_builder, script_dir, tmp_path):
    test_script = 'pyi_frozen_stdlib_modules.py'
    ref_result_file = tmp_path / 'ref_results.txt'
    result_file = tmp_path / 'results.txt'

    # Run the test script unfrozen, to obtain reference results
    ret = compat.exec_python_rc(
        str(script_dir / test_script),
        str(ref_result_file),
    )
    assert ret == 0, "Unfrozen test script failed!"

    # Freeze and run the test script
    pyi_builder.test_script(
        test_script,
        app_args=[str(result_file)],
    )

    # Process the results
    def _normalize_module_path(module_path, stdlib_dir):
        if not module_path:
            return module_path
        module_path, ext = os.path.splitext(os.path.relpath(module_path, stdlib_dir))
        assert ext in ('.pyc', '.py')
        return module_path

    def _load_results(filename):
        # Read pprint-ed results
        with open(filename, 'r', encoding='utf-8') as fp:
            data = fp.read()
        data = eval(data)

        # First entry is sys._stdlib_dir
        stdlib_dir = data[0]

        results = []
        for name, file_attr, state_filename, state_origname in data[1:]:
            # Remove sys._stdlib_dir prefix from __file__ attribute and filename from __spec__.loader_state, and remove
            # the .py/.pyc suffix for easier comparison.
            results.append((
                name,
                _normalize_module_path(file_attr, stdlib_dir),
                _normalize_module_path(state_filename, stdlib_dir),
                state_origname,
            ))

        return results

    ref_results = _load_results(ref_result_file)
    results = _load_results(result_file)

    assert results == ref_results


# Test whether dis can disassemble the __main__ module, as per #5897.
def test_dis_main(pyi_builder):
    pyi_builder.test_source(
        """
        import dis
        import sys

        print(dis.dis(sys.modules["__main__"].__loader__.get_code("__main__")))
        """
    )


# Test that setting utf8 X-flag controls the PEP540 UTF-8 mode on all OSes, regardless of current locale setting.
@pytest.mark.parametrize('xflag,enabled', [("X utf8", True), ("X utf8=1", True), ("X utf8=0", False)])
def test_utf8_mode_xflag(xflag, enabled, pyi_builder):
    pyi_builder.test_source(
        f"""
        import sys
        print("sys.flags:", sys.flags)
        assert sys.flags.utf8_mode == {enabled}
        """,
        pyi_args=["--python-option", xflag]
    )


# Test that PEP540 UTF-8 mode is automatically enabled for C and POSIX locales (applicable only to macOS and linux).
@pytest.mark.linux
@pytest.mark.darwin
@pytest.mark.parametrize('locale', ['C', 'POSIX'])
def test_utf8_mode_locale(locale, pyi_builder, monkeypatch):
    monkeypatch.setenv('LC_CTYPE', locale)
    monkeypatch.setenv('LC_ALL', locale)  # Required by macOS CI; setting just LC_CTYPE is not enough.
    pyi_builder.test_source(
        """
        import sys
        print("sys.flags:", sys.flags)
        assert sys.flags.utf8_mode == 1
        """
    )


# Test that setting dev X-flag controls dev mode.
@pytest.mark.parametrize('xflag,enabled', [("X dev", True), ("X dev=1", True), ("X dev=0", False)])
def test_dev_mode_xflag(xflag, enabled, pyi_builder):
    pyi_builder.test_source(
        f"""
        import sys
        print("sys.flags:", sys.flags)
        assert sys.flags.dev_mode == {enabled}
        """,
        pyi_args=["--python-option", xflag]
    )


# Test that setting hash seed to zero via --python-option disables hash randomization.
def test_disable_hash_randomization(pyi_builder):
    pyi_builder.test_source(
        """
        import sys
        print("sys.flags:", sys.flags)
        assert sys.flags.hash_randomization == 0
        """,
        pyi_args=["--python-option", "hash_seed=0"]
    )


# Test that onefile cleanup does not remove contents of a directory that user symlinks into sys._MEIPASS (see #6074).
@onefile_only
def test_onefile_cleanup_symlinked_dir(pyi_builder, tmp_path):
    # Create output directory with five pre-existing files
    output_dir = tmp_path / 'output_dir'
    output_dir.mkdir()
    for idx in range(5):
        output_file = output_dir / f'preexisting-{idx}.txt'
        output_file.write_text(f"Pre-existing file #{idx}", encoding='utf-8')

    # Check if OS supports creation of symbolic links
    try:
        (tmp_path / 'testdir').symlink_to(output_dir)
    except OSError:
        pytest.skip("OS does not support (unprivileged) creation of symbolic links.")

    # Run the test program
    pyi_builder.test_source(
        """
        import sys
        import os

        # Output directory is passed via argv[1]; create symlink to it inside the _MEIPASS
        output_dir = os.path.join(sys._MEIPASS, 'output')
        os.symlink(sys.argv[1], output_dir)

        # Create five files
        for idx in range(5):
            output_file = os.path.join(output_dir, f'output-{idx}.txt')
            with open(output_file, 'w', encoding='utf-8') as fp:
                fp.write(f'Output file #{idx}')
        """,
        app_args=[output_dir]
    )

    # Output directory should contain all five pre-existing and five new files.
    for idx in range(5):
        output_file = output_dir / f'preexisting-{idx}.txt'
        assert output_file.is_file()
    for idx in range(5):
        output_file = output_dir / f'output-{idx}.txt'
        assert output_file.is_file()


# Test that single-file metadata (as commonly found in Debian/Ubuntu packages) is properly collected by copy_metadata().
def test_single_file_metadata(pyi_builder):
    # Add directory containing the my-test-package metadata to search path
    extra_path = _MODULES_DIR / "pyi_single_file_metadata"

    pyi_builder.test_source(
        """
        import pkg_resources

        # The pkg_resources.get_distribution() call automatically triggers collection of the metadata. While it does not
        # raise an error if metadata is not found while freezing, the calls below will fall at run-time in that case.
        dist = pkg_resources.get_distribution('my-test-package')

        # Sanity check
        assert dist.project_name == 'my-test-package'
        assert dist.version == '1.0'
        assert dist.egg_name() == f'my_test_package-{dist.version}-py{sys.version_info[0]}.{sys.version_info[1]}'
        """,
        pyi_args=['--paths', str(extra_path)]
    )


# Test that we can successfully package a program even if one of its modules contains non-ASCII characters in a local
# (non-UTF8) encoding and fails to declare such encoding using PEP361 encoding header.
def test_program_importing_module_with_invalid_encoding1(pyi_builder):
    # Add directory containing the my-test-package metadata to search path
    extra_path = _MODULES_DIR / "pyi_module_with_invalid_encoding"

    pyi_builder.test_source(
        """
        import mymodule1
        assert mymodule1.hello() == "hello"
        """,
        pyi_args=['--paths', str(extra_path)]
    )


def test_program_importing_module_with_invalid_encoding2(pyi_builder):
    # Add directory containing the my-test-package metadata to search path
    extra_path = _MODULES_DIR / "pyi_module_with_invalid_encoding"

    pyi_builder.test_source(
        """
        import mymodule2
        assert mymodule2.hello() == "hello"
        """,
        pyi_args=['--paths', str(extra_path)]
    )


# Test that collection of an executable shell script (essentially a data file with executable bit) preserves its
# executable bit.
@pytest.mark.linux
@pytest.mark.darwin
def test_bundled_shell_script(pyi_builder, tmp_path):
    script_file = tmp_path / "test_script.sh"
    with open(script_file, "w", encoding="utf-8") as fp:
        print('#!/bin/sh', file=fp)
        print('echo "Hello world!"', file=fp)
    script_file.chmod(0o755)

    pyi_builder.test_source(
        """
        import os
        import subprocess

        script = os.path.join(os.path.dirname(__file__), 'test_script.sh')
        output = subprocess.check_output(script, text=True)

        print(output)
        assert output.strip() == "Hello world!"
        """,
        pyi_args=['--add-data', f"{script_file}:."]
    )


# Test that a program importing `__main__` module does not pull in `PyInstaller` (or in the case of the test, the
# `pytest`). The problem is that the `__main__` has different meaning during analysis vs. during program's run;
# during analysis, it resolves to the entry-point module that is running the analysis, whereas during program run, it
# refers to the program's entry-point. Currently, this seems to be a problem only on Windows, where modulegraph manages
# to resolve `__main__` into `.../PyInstaller.exe/__main__.py` (or `.../pytest.exe/__main__.py`). On Linux and macOS,
# modulegraph does not seem to be able to resolve `__main__`.
def test_import_main_should_not_collect_pyinstaller1(pyi_builder):
    hooks_dir = _MODULES_DIR / 'pyi_import_main' / 'hooks'
    pyi_builder.test_source(
        """
        # Plain import.
        import __main__
        print(__main__)
        """,
        pyi_args=['--additional-hooks-dir', str(hooks_dir)]
    )


def test_import_main_should_not_collect_pyinstaller2(pyi_builder):
    hooks_dir = _MODULES_DIR / 'pyi_import_main' / 'hooks'
    pyi_builder.test_source(
        """
        # Import __main__ in the same way as `pkg_resources` and its vendored variants
        # (e.g., `pip._vendor.pkg_resources`) do.
        try:
            from __main__ import __requires__
        except ImportError:
            pass
        """,
        pyi_args=['--additional-hooks-dir', str(hooks_dir)]
    )


# Test that a relative import attempt of a missing optional sub-module in a package does not trigger collection of an
# unrelated but eponymous top-level module. Simulates the scenario from #8010, where the following block in
# `openpyxl.reader.excel`:
#
# ```
# try:
#    from ..tests import KEEP_VBA
# except ImportError:
#    KEEP_VBA = False
# ```
#
# (https://foss.heptapod.net/openpyxl/openpyxl/-/blob/branch/3.1/openpyxl/reader/excel.py#L16)
#
# triggers collection of top-level `tests` package that is provided by the `LaoNLP` distribution. And importing
# the said `tests` package during analysis triggers LaoNLP's unit tests...
def test_missing_relative_import_collects_unrelated_top_level_module(pyi_builder):
    extra_path = _MODULES_DIR / "pyi_missing_relative_import"
    hooks_dir = extra_path / 'hooks'

    pyi_builder.test_source(
        """
        import mypackage
        """,
        pyi_args=['--additional-hooks-dir', str(hooks_dir), '--paths', str(extra_path)]
    )  # yapf: disable


# Test that various forms of relative imports are properly caught by the module exclusion.
@pytest.mark.parametrize('exclude', [False, True], ids=["baseline", "exclude"])
def test_excluded_relative_imports(pyi_builder, exclude):
    extra_path = _MODULES_DIR / "pyi_excluded_relative_imports"
    hooks_dir = extra_path / 'hooks'

    pyi_args = ['--paths', str(extra_path)]
    if exclude:
        pyi_args += ['--additional-hooks-dir', str(hooks_dir)]

    pyi_builder.test_source(
        f"""
        import os
        os.environ['_FORBIDDEN_MODULES_ENABLED'] = '{str(int(not exclude))}'  # '0' or '1'

        import mypackage
        """,
        pyi_args=pyi_args,
    )


# Test the bytecode optimization settings (either implicit via python interpreter options or explicit via the new
# optimize option).
def _test_optimization(pyi_builder, level, tmp_path, pyi_args):
    extra_path = _MODULES_DIR / "pyi_optimization"
    results_filename = tmp_path / "results.json"

    pyi_args = ["--path", str(extra_path), *pyi_args]

    pyi_builder.test_script("pyi_optimization.py", pyi_args=pyi_args, app_args=[str(results_filename)])

    with open(results_filename, "r", encoding="utf-8") as fp:
        results = json.load(fp)

    # Check that sys.flags.optimize matches the specified level
    runtime_level = results["sys.flags.optimize"]
    assert runtime_level == level, \
        f"Unexpected sys.flags.optimize value! Expected {level}, found {runtime_level}!"

    def _check_flag(results, area, flag, expected_value):
        value = results[area][flag]
        assert value == expected_value, \
            f"Unexpected value for {flag!r} in {area!r}. Expected {expected_value!r}, found {value!r}"

    # Check results for entry-point script
    _check_flag(results, "script", "has_debug", level < 1)
    _check_flag(results, "script", "has_assert", level < 1)
    _check_flag(results, "script", "function_has_doc", level < 2)

    # Check results for module
    _check_flag(results, "module", "has_debug", level < 1)
    _check_flag(results, "module", "has_assert", level < 1)
    _check_flag(results, "module", "module_has_doc", level < 2)
    _check_flag(results, "module", "function_has_doc", level < 2)


@pytest.mark.parametrize('level', [0, 1, 2], ids=["unspecified", "O", "OO"])
def test_optimization_via_python_option(pyi_builder, level, tmp_path):
    pyi_args = level * ["--python", "O"]

    # If no "--python O" flags are supplied, the optimization level is set to `sys.flags.optimize`.
    if not pyi_args:
        level = sys.flags.optimize

    _test_optimization(pyi_builder, level, tmp_path, pyi_args)


@pytest.mark.parametrize('level', [0, 1, 2])
def test_optimization_via_optimize_option(pyi_builder, level, tmp_path):
    pyi_args = ["--optimize", str(level)]
    _test_optimization(pyi_builder, level, tmp_path, pyi_args)


# Test that runpy.run_path() in frozen application can run a bundled python script file. See #8767.
def test_runpy_run_from_location(tmp_path, pyi_builder):
    script_file = tmp_path / "script.py"
    script_file.write_text("""print("Hello world!")\n""", encoding='utf-8')

    pyi_builder.test_source(
        """
        import os
        import sys
        import runpy

        script_file = os.path.join(sys._MEIPASS, 'script.py')
        runpy.run_path(script_file, run_name="__main__")
        """,
        pyi_args=['--add-data', f"{script_file}:."],
    )


# End-to-end tests with --add-data and source paths with and without glob.
@pytest.mark.parametrize('scenario', ['recursive_noglob', 'recursive_glob', 'top_level_files'])
def test_recursive_add_data(pyi_builder, scenario):
    data_dir = pathlib.Path(__file__).parent / 'data' / 'recursive_add_data' / 'data-dir'

    if scenario == 'top_level_files':
        add_data_arg = data_dir / '*.txt'
        expected_files = [
            "data-dir/file1.txt",
            "data-dir/file2.txt",
        ]
    else:
        if scenario == 'recursive_noglob':
            add_data_arg = data_dir
        else:
            add_data_arg = data_dir / '*'
        expected_files = [
            "data-dir/dir1/dir1/file1.txt",
            "data-dir/dir1/dir1/file2.txt",
            "data-dir/dir1/dir2/file1.txt",
            "data-dir/dir1/file1.txt",
            "data-dir/dir2/dir1/file1.txt",
            "data-dir/dir2/dir1/file2.txt",
            "data-dir/dir3/dir1/file1.txt",
            "data-dir/dir3/file1.txt",
            "data-dir/dir3/file2.txt",
            "data-dir/file1.txt",
            "data-dir/file2.txt",
        ]

    pyi_builder.test_source(
        """
        import pathlib
        import sys

        root_directory = pathlib.Path(__file__).parent

        # File names to check are passed as command-line arguments; each
        # file is expected to contain its relative path (with POSIX separators).
        for entry in sys.argv[1:]:
            file_path = root_directory / entry
            assert file_path.is_file(), f"File {str(file_path)!r} does not exist!"

            content = file_path.read_text().strip()
            assert content == entry, f"Unexpected content in {str(file_path)!r}: found {content!r}, expected {entry!r}!"
        """,
        pyi_args=['--add-data', f'{add_data_arg!s}:data-dir'],
        app_args=[*expected_files],
    )
