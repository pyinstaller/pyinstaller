#-----------------------------------------------------------------------------
# Copyright (c) 2005-2023, PyInstaller Development Team.
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
import shutil
import re

from PyInstaller.utils import hooks as hookutils
from PyInstaller.compat import exec_python, is_win, is_cygwin
from PyInstaller.utils.tests import skipif
from PyInstaller import log as logging

# Cygwin uses .dll suffix for extension modules, which several tests fail to properly account for.
incompatible_with_cygwin = skipif(
    is_cygwin,
    reason="Does not account for the .dll suffix used for extension modules under Cygwin.",
)


class TestRemovePrefix(object):
    # Verify that removing a prefix from an empty string is OK.
    def test_empty_string(self):
        assert '' == hookutils.remove_prefix('', 'prefix')

    # An empty prefix should pass the string through unmodified.
    def test_emptystr_unmodif(self):
        assert 'test' == hookutils.remove_prefix('test', '')

    # If the string is the prefix, it should be empty at exit.
    def test_string_prefix(self):
        assert '' == hookutils.remove_prefix('test', 'test')

    # Just the prefix should be removed.
    def test_just_prefix(self):
        assert 'ing' == hookutils.remove_prefix('testing', 'test')

    # A matching string not as prefix should produce no modifications
    def test_no_modific(self):
        assert 'atest' == hookutils.remove_prefix('atest', 'test')


class TestRemoveSuffix(object):
    # Verify that removing a suffix from an empty string is OK.
    def test_empty_string(self):
        assert '' == hookutils.remove_suffix('', 'suffix')

    # An empty suffix should pass the string through unmodified.
    def test_emptystr_unmodif(self):
        assert 'test' == hookutils.remove_suffix('test', '')

    # If the string is the suffix, it should be empty at exit.
    def test_string_suffix(self):
        assert '' == hookutils.remove_suffix('test', 'test')

    # Just the suffix should be removed.
    def test_just_suffix(self):
        assert 'test' == hookutils.remove_suffix('testing', 'ing')

    # A matching string not as suffix should produce no modifications
    def test_no_modific(self):
        assert 'testa' == hookutils.remove_suffix('testa', 'test')


class TestRemoveExtension(object):
    # Removing a suffix from a filename with no extension returns the filename.
    def test_no_extension(self):
        assert 'file' == hookutils.remove_file_extension('file')

    # A filename with two extensions should have only the first removed.
    def test_two_extensions(self):
        assert 'file.1' == hookutils.remove_file_extension('file.1.2')

    # Standard case - remove an extension
    def test_remove_ext(self):
        assert 'file' == hookutils.remove_file_extension('file.1')

    # Unix-style .files are not treated as extensions
    def test_unixstyle_not_ext(self):
        assert '.file' == hookutils.remove_file_extension('.file')

    # Unix-style .file.ext works
    def test_unixstyle_ext(self):
        assert '.file' == hookutils.remove_file_extension('.file.1')

    # Unix-style .file.ext works
    def test_unixstyle_path(self):
        assert '/a/b/c' == hookutils.remove_file_extension('/a/b/c')
        assert '/a/b/c' == hookutils.remove_file_extension('/a/b/c.1')

    # Windows-style .file.ext works
    def test_win32style_path(self):
        assert 'C:\\a\\b\\c' == hookutils.remove_file_extension('C:\\a\\b\\c')
        assert 'C:\\a\\b\\c' == hookutils.remove_file_extension('C:\\a\\b\\c.1')


# The name of the hookutils test files directory
TEST_MOD = 'hookutils_package'
# The path to this directory.
TEST_MOD_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hookutils_files')


@pytest.fixture
def mod_list(monkeypatch):
    monkeypatch.syspath_prepend(TEST_MOD_PATH)
    # Use the hookutils_test_files package for testing.
    return hookutils.collect_submodules(TEST_MOD)


class TestCollectSubmodules(object):
    # A message should be emitted if a module, not a package, was passed.
    # The module's name should be in the returned list, nevetheless.
    def test_collect_submod_module(self, caplog):
        with caplog.at_level(logging.DEBUG, logger='PyInstaller.utils.hooks'):
            assert hookutils.collect_submodules('os') == ['os']
            assert "collect_submodules - os is not a package." in caplog.records[-1].getMessage()

    # A TypeError should be raised if given something other than a str.
    def test_not_a_string(self):
        with pytest.raises(TypeError, match="package must be a str"):
            hookutils.collect_submodules(os)

    # The package name itself should be in the returned list.
    def test_collect_submod_itself(self, mod_list):
        assert TEST_MOD in mod_list

    # Python extension is included in the list.
    @incompatible_with_cygwin
    def test_collect_submod_pyextension(self, mod_list):
        assert TEST_MOD + '.pyextension' in mod_list

    # Check that all packages get included
    # NOTE: the new behavior (see #6846 and #6850) is that un-importable subpackages are not included.
    @incompatible_with_cygwin
    def test_collect_submod_all_included(self, mod_list):
        mod_list.sort()
        assert mod_list == [
            TEST_MOD,
            # Python extensions end with '.pyd' on Windows and with  '.so' on Linux, macOS, and other OSes.
            # Under Cygwin, '.dll' suffix is used for extensions; therefore, the premise and the test data used by
            # this test is inherently incompatible with Cygwin.
            TEST_MOD + '.pyextension',
            #TEST_MOD + '.raises_error_on_import_1',
            #TEST_MOD + '.raises_error_on_import_2',
            TEST_MOD + '.subpkg',
            TEST_MOD + '.subpkg.twelve',
            TEST_MOD + '.two'
        ]

    # Dynamic libraries (.dll, .dylib) are not included in the list.
    @incompatible_with_cygwin
    def test_collect_submod_no_dynamiclib(self, mod_list):
        assert TEST_MOD + '.dynamiclib' not in mod_list

    # Subpackages without an __init__.py should not be included.
    def test_collect_submod_subpkg_init(self, mod_list):
        assert TEST_MOD + '.py_files_not_in_package.sub_pkg.three' not in mod_list

    # Test with a subpackage.
    def test_collect_submod_subpkg(self, mod_list):
        # Note: Even though mod_list is overwritten, it is still needed as a fixture, so that the path to the
        # TEST_MOD is set correctly.
        mod_list = hookutils.collect_submodules(TEST_MOD + '.subpkg')
        mod_list.sort()
        assert mod_list == [TEST_MOD + '.subpkg', TEST_MOD + '.subpkg.twelve']

    # Test in an ``.egg`` file.
    @incompatible_with_cygwin  # calls `test_collect_submod_all_included`
    def test_collect_submod_egg(self, tmp_path, monkeypatch):
        # Copy files to a tmpdir for egg building.
        dest_path = tmp_path / 'hookutils_package'
        shutil.copytree(TEST_MOD_PATH, dest_path)
        monkeypatch.chdir(dest_path)

        # Create an egg from the test package. For debug, show the output of the egg build.
        print(exec_python('setup.py', 'bdist_egg'))

        # Obtain the name of the egg, which depends on the Python version.
        dist_path = dest_path / 'dist'
        fl = os.listdir(dist_path)
        assert len(fl) == 1
        egg_name = fl[0]
        assert egg_name.endswith('.egg')

        # Add the egg to Python's path.
        pth = str(dist_path / egg_name)
        monkeypatch.setattr('PyInstaller.config.CONF', {'pathex': [pth]})
        monkeypatch.syspath_prepend(pth)

        # Verify its contents.
        ml = hookutils.collect_submodules(TEST_MOD)
        self.test_collect_submod_all_included(ml)

    # Messages printed to stdout by modules during collect_submodules() should not affect the collected modules list.
    def test_collect_submod_stdout_interference(self, monkeypatch):
        TEST_MOD = 'foo'
        TEST_MOD_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hookutils_files2')

        monkeypatch.setattr('PyInstaller.config.CONF', {'pathex': [TEST_MOD_PATH]})
        monkeypatch.syspath_prepend(TEST_MOD_PATH)

        ml = hookutils.collect_submodules(TEST_MOD)
        ml = sorted(ml)

        assert ml == ['foo', 'foo.bar']

    # Test each possible value for the **on_error** parameter to collect_submodules().
    def test_error_propagation(self, capfd, monkeypatch):
        monkeypatch.setattr('PyInstaller.config.CONF', {'pathex': [TEST_MOD_PATH]})
        monkeypatch.syspath_prepend(TEST_MOD_PATH)

        # Test the default of warning only for the 1st error.
        hookutils.collect_submodules(TEST_MOD)
        error = capfd.readouterr().err
        # Note that there is no guarantee which submodule will be collected first so we don't know exactly what the
        # error will be from raises_error_on_import_1 or raises_error_on_import_2.
        assert re.match(
            ".*Failed .* for 'hookutils_package.raises_error_on_import_[12]' because .* "
            "raised: AssertionError: I cannot be imported", error
        )
        # Make sure that only one warning was issued.
        assert error.count("Failed") == 1

        # Test ignore everything.
        hookutils.collect_submodules(TEST_MOD, on_error="ignore")
        assert capfd.readouterr().err == ''

        # Test warning for all errors. There should be two in total.
        hookutils.collect_submodules(TEST_MOD, on_error="warn")
        error = capfd.readouterr().err
        assert "raises_error_on_import_1" in error
        assert "raises_error_on_import_2" in error
        assert error.count("Failed") == 2

        # Test treating errors as errors.
        with pytest.raises(RuntimeError) as ex_info:
            hookutils.collect_submodules(TEST_MOD, on_error="raise")
            # The traceback should include the cause of the error...
            assert ex_info.match('(?s).* assert 0, "I cannot be imported!"')
            # ... and the name of the offending submodule in an easy to spot format.
            assert ex_info.match("Unable to load submodule 'hookutils_package.raises_error_on_import_[12]'")


def test_is_module_or_submodule():
    assert hookutils.is_module_or_submodule('foo.bar', 'foo.bar')
    assert hookutils.is_module_or_submodule('foo.bar.baz', 'foo.bar')
    assert not hookutils.is_module_or_submodule('foo.bard', 'foo.bar')
    assert not hookutils.is_module_or_submodule('foo', 'foo.bar')


def test_check_requirement_package_not_installed():
    assert hookutils.check_requirement('pytest')
    assert not hookutils.check_requirement('magnumopus-no-package-test-case')


# An error should be raised if a module, not a package, was passed.
def test_collect_data_module():
    # 'os' is a module, not a package.
    with pytest.raises(TypeError):
        hookutils.collect_data_files(__import__('os'))


# This fixtures runs ``collect_data_files`` through the test cases in ``_DATA_PARAMS``.
@pytest.fixture(
    params=[
        # This is used to invoke ``collect_data_files(*args, **kwargs)`` and provide the expected results
        # for validation. The order is: args, kwargs, expected_results_sequence
        (
            [TEST_MOD],
            {},
            (
                'dynamiclib.dll',
                'dynamiclib.dylib',
                'nine.dat',
                os.path.join('py_files_not_in_package', 'data', 'eleven.dat'),
                os.path.join('py_files_not_in_package', 'ten.dat'),
                # Not backwards! On Windows, ``.so`` files are just data and vice versa.
                'pyextension.so' if is_win else 'pyextension.pyd',
                os.path.join('subpkg', 'thirteen.txt'),
            ),
        ),
        # Test collecting from a subpackage.
        (
            [TEST_MOD + '.subpkg'],
            {},
            (os.path.join('subpkg', 'thirteen.txt'),),
        ),
        (
            [TEST_MOD],
            dict(include_py_files=True, excludes=['**/__pycache__']),
            (
                '__init__.py',
                'dynamiclib.dll',
                'dynamiclib.dylib',
                'nine.dat',
                os.path.join('py_files_not_in_package', 'data', 'eleven.dat'),
                os.path.join('py_files_not_in_package', 'one.py'),
                os.path.join('py_files_not_in_package', 'sub_pkg', '__init__.py'),
                os.path.join('py_files_not_in_package', 'sub_pkg', 'three.py'),
                os.path.join('py_files_not_in_package', 'ten.dat'),
                # Not backwards! On Windows, ``.so`` files are just data and vice versa.
                'pyextension.so' if is_win else 'pyextension.pyd',
                os.path.join('raises_error_on_import_1', '__init__.py'),
                os.path.join('raises_error_on_import_1', 'foo.py'),
                os.path.join('raises_error_on_import_2', '__init__.py'),
                os.path.join('raises_error_on_import_2', 'foo.py'),
                os.path.join('subpkg', '__init__.py'),
                os.path.join('subpkg', 'thirteen.txt'),
                os.path.join('subpkg', 'twelve.py'),
                'two.py',
            ),
        ),
        (
            [TEST_MOD],
            dict(excludes=['py_files_not_in_package', '**/__pycache__']),
            (
                'dynamiclib.dll',
                'dynamiclib.dylib',
                'nine.dat',
                'pyextension.so' if is_win else 'pyextension.pyd',
                os.path.join('subpkg', 'thirteen.txt'),
            ),
        ),
        (
            [TEST_MOD],
            dict(includes=['**/*.dat', '**/*.txt']),
            (
                'nine.dat',
                os.path.join('py_files_not_in_package', 'data', 'eleven.dat'),
                os.path.join('py_files_not_in_package', 'ten.dat'),
                os.path.join('subpkg', 'thirteen.txt'),
            ),
        ),
        (
            [TEST_MOD],
            dict(includes=['*.dat']),
            ('nine.dat',),
        ),
        (
            [TEST_MOD],
            dict(subdir="py_files_not_in_package", excludes=['**/__pycache__']),
            (
                os.path.join('py_files_not_in_package', 'data', 'eleven.dat'),
                os.path.join('py_files_not_in_package', 'ten.dat'),
            ),
        ),
    ],
    ids=['package', 'subpackage', 'package with py files', 'excludes', '** includes', 'includes', 'subdir']
)
def data_lists(monkeypatch, request):
    def _sort(sequence):
        sorted_list = sorted(list(sequence))
        return tuple(sorted_list)

    # Add path with 'hookutils_files' module to ``sys.path`` (so analysis in the main process can find it),
    # and to ``pathex`` (so subprocess-isolated code can find it).
    monkeypatch.setattr('PyInstaller.config.CONF', {'pathex': [TEST_MOD_PATH]})
    monkeypatch.syspath_prepend(TEST_MOD_PATH)
    # Use the hookutils_test_files package for testing.
    args, kwargs, subfiles = request.param
    data = hookutils.collect_data_files(*args, **kwargs)
    # Break list of (source, dest) into source and dest lists.
    src = [item[0] for item in data]
    dst = [item[1] for item in data]

    return subfiles, _sort(src), _sort(dst)


# Make sure the correct files are found.
@incompatible_with_cygwin
def test_collect_data_all_included(data_lists):
    subfiles, src, dst = data_lists
    # Check the source and dest lists against the correct values in subfiles.
    src_compare = tuple([os.path.join(TEST_MOD_PATH, TEST_MOD, subpath) for subpath in subfiles])
    dst_compare = [os.path.dirname(os.path.join(TEST_MOD, subpath)) for subpath in subfiles]
    dst_compare.sort()
    dst_compare = tuple(dst_compare)
    assert src == src_compare
    assert dst == dst_compare


# An ImportError should be raised if the module is not found.
def test_get_module_file_attribute_non_exist_module():
    with pytest.raises(ImportError):
        hookutils.get_module_file_attribute('pyinst_nonexisting_module_name')
