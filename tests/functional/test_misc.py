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

import pytest

from PyInstaller import compat

# Directory with testing modules used in some tests.
_MODULES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modules')


# Test that in python 3.11 and later, sys._stdlib_dir is set and that python-frozen modules have __file__ attribute.
@pytest.mark.skipif(not compat.is_py311, reason="applicable only to python >= 3.11")
def test_frozen_stdlib_modules(pyi_builder, script_dir, tmpdir):
    test_script = 'pyi_frozen_stdlib_modules.py'
    ref_result_file = os.path.join(tmpdir, 'ref_results.txt')
    result_file = os.path.join(tmpdir, 'results.txt')

    # Run the test script unfrozen, to obtain reference results
    ret = compat.exec_python_rc(
        os.path.join(script_dir, test_script),
        ref_result_file,
    )
    assert ret == 0, "Unfrozen test script failed!"

    # Freeze and run the test script
    pyi_builder.test_script(
        test_script,
        app_args=[result_file],
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
        with open(filename, 'r') as fp:
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


# Test inspect.getmodule() on stack-frames obtained by inspect.stack(). Reproduces the issue reported by #5963 while
# expanding the test to cover a package and its submodule in addition to the __main__ module.
def test_inspect_getmodule_from_stackframes(pyi_builder):
    pathex = os.path.join(_MODULES_DIR, 'pyi_inspect_getmodule_from_stackframes')
    # NOTE: run_from_path MUST be True, otherwise cwd + rel_path coincides with sys._MEIPASS + rel_path and masks the
    #       path resolving issue in onedir builds.
    pyi_builder.test_source(
        """
        import helper_package

        # helper_package.test_call_chain() calls eponymous function in helper_package.helper_module, which in turn uses
        # inspect.stack() and inspect.getmodule() to obtain list of modules involved in the chain call.
        modules = helper_package.test_call_chain()

        # Expected call chain
        expected_module_names = [
            'helper_package.helper_module',
            'helper_package',
            '__main__'
        ]

        # All modules must have been resolved
        assert not any(module is None for module in modules)

        # Verify module names
        module_names = [module.__name__ for module in modules]
        assert module_names == expected_module_names
        """,
        pyi_args=['--paths', pathex],
        run_from_path=True
    )


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
        """
        import sys
        print("sys.flags:", sys.flags)
        assert sys.flags.utf8_mode == {}
        """.format(enabled),
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
        """
        import sys
        print("sys.flags:", sys.flags)
        assert sys.flags.dev_mode == {}
        """.format(enabled),
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
def test_onefile_cleanup_symlinked_dir(pyi_builder, tmpdir):
    if pyi_builder._mode != 'onefile':
        pytest.skip('The test is relevant only to onefile builds.')

    # Create output directory with five pre-existing files
    output_dir = str(tmpdir / 'output_dir')
    os.mkdir(output_dir)
    for idx in range(5):
        output_file = os.path.join(output_dir, f'preexisting-{idx}.txt')
        with open(output_file, 'w') as fp:
            fp.write(f'Pre-existing file #{idx}')

    # Check if OS supports creation of symbolic links
    try:
        os.symlink(output_dir, str(tmpdir / 'testdir'))
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
            with open(output_file, 'w') as fp:
                fp.write(f'Output file #{idx}')
        """,
        app_args=[output_dir]
    )

    # Output directory should contain all five pre-existing and five new files.
    for idx in range(5):
        output_file = os.path.join(output_dir, f'preexisting-{idx}.txt')
        assert os.path.isfile(output_file)
    for idx in range(5):
        output_file = os.path.join(output_dir, f'output-{idx}.txt')
        assert os.path.isfile(output_file)


# Test that single-file metadata (as commonly found in Debian/Ubuntu packages) is properly collected by copy_metadata().
def test_single_file_metadata(pyi_builder):
    # Add directory containing the my-test-package metadata to search path
    extra_path = os.path.join(_MODULES_DIR, "pyi_single_file_metadata")

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
        pyi_args=['--paths', extra_path]
    )


# Test that we can successfully package a program even if one of its modules contains non-ASCII characters in a local
# (non-UTF8) encoding and fails to declare such encoding using PEP361 encoding header.
def test_program_importing_module_with_invalid_encoding1(pyi_builder):
    # Add directory containing the my-test-package metadata to search path
    extra_path = os.path.join(_MODULES_DIR, "pyi_module_with_invalid_encoding")

    pyi_builder.test_source(
        """
        import mymodule1
        assert mymodule1.hello() == "hello"
        """,
        pyi_args=['--paths', extra_path]
    )


def test_program_importing_module_with_invalid_encoding2(pyi_builder):
    # Add directory containing the my-test-package metadata to search path
    extra_path = os.path.join(_MODULES_DIR, "pyi_module_with_invalid_encoding")

    pyi_builder.test_source(
        """
        import mymodule2
        assert mymodule2.hello() == "hello"
        """,
        pyi_args=['--paths', extra_path]
    )


# Test the robustness of `inspect` run-time hook w.r.t. to the issue #7642.
#
# If our run-time hook imports a module in the global namespace and attempts to use this module in a function that
# might get called later on in the program (e.g., a function override or registered callback function), we are at the
# mercy of user's program, which might re-bind the module's name to something else (variable, function), leading to
# an error.
#
# This particular test will raise:
# ```
# Traceback (most recent call last):
#  File "test_source.py", line 17, in <module>
#  File "test_source.py", line 14, in some_interactive_debugger_function
#  File "inspect.py", line 1755, in stack
#  File "inspect.py", line 1730, in getouterframes
#  File "inspect.py", line 1688, in getframeinfo
#  File "PyInstaller/hooks/rthooks/pyi_rth_inspect.py", line 22, in _pyi_getsourcefile
# AttributeError: 'function' object has no attribute 'getfile'
# ```
def test_inspect_rthook_robustness(pyi_builder):
    pyi_builder.test_source(
        """
        # A custom function in global namespace that happens to have name clash with `inspect` module.
        def inspect(something):
            print(f"Inspecting {something}: type is {type(something)}")


        # A call to `inspect.stack` function somewhere deep in an interactive debugger framework.
        # This eventually ends up calling our `_pyi_getsourcefile` override in the `inspect` run-time hook. The
        # override calls `inspect.getfile`; if the run-time hook imported `inspect` in a global namespace, the
        # name at this point is bound the the custom function that program defined, leading to an error.
        def some_interactive_debugger_function():
            import inspect
            print(f"Current stack: {inspect.stack()}")


        some_interactive_debugger_function()
        """
    )
