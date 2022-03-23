#-----------------------------------------------------------------------------
# Copyright (c) 2021-2022, PyInstaller Development Team.
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

# Directory with testing modules used in some tests.
_MODULES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modules')


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


# Test that setting PYTHONUTF8 controls the PEP540 UTF-8 mode on all OSes, regardless of current locale setting.
@pytest.mark.parametrize('python_utf8', [True, False])
def test_utf8_mode_envvar(python_utf8, pyi_builder, monkeypatch):
    monkeypatch.setenv('PYTHONUTF8', str(int(python_utf8)))
    pyi_builder.test_source(
        """
        import sys
        assert sys.flags.utf8_mode == {}
        """.format(python_utf8)
    )


# Test that PEP540 UTF-8 mode is automatically enabled for C and POSIX locales (applicable only to macOS and linux).
@pytest.mark.linux
@pytest.mark.darwin
@pytest.mark.parametrize('locale', ['C', 'POSIX'])
def test_utf8_mode_locale(locale, pyi_builder, monkeypatch):
    monkeypatch.setenv('LC_CTYPE', locale)
    monkeypatch.setenv('LC_ALL', locale)  # Required by macOS CI; setting just LC_CTYPE is not enough.
    pyi_builder.test_source("""
        import sys
        assert sys.flags.utf8_mode == 1
        """)


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
