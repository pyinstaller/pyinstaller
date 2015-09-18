#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import os
import pytest

from os.path import join
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, get_module_file_attribute
from PyInstaller.utils.hooks import remove_prefix, remove_suffix
from PyInstaller.utils.hooks import remove_file_extension


class TestRemovePrefix(object):
    # Verify that removing a prefix from an empty string is OK.
    def test_empty_string(self):
        assert '' == remove_prefix('', 'prefix')

    # An empty prefix should pass the string through unmodified.
    def test_emptystr_unmodif(self):
        assert 'test' == remove_prefix('test', '')

    # If the string is the prefix, it should be empty at exit.
    def test_string_prefix(self):
        assert '' == remove_prefix('test', 'test')

    # Just the prefix should be removed.
    def test_just_prefix(self):
        assert 'ing' == remove_prefix('testing', 'test')

    # A matching string not as prefix should produce no modifications
    def test_no_modific(self):
        assert 'atest' == remove_prefix('atest', 'test')


class TestRemoveSuffix(object):
    # Verify that removing a suffix from an empty string is OK.
    def test_empty_string(self):
        assert '' == remove_suffix('', 'suffix')

    # An empty suffix should pass the string through unmodified.
    def test_emptystr_unmodif(self):
        assert 'test' == remove_suffix('test', '')

    # If the string is the suffix, it should be empty at exit.
    def test_string_suffix(self):
        assert '' == remove_suffix('test', 'test')

    # Just the suffix should be removed.
    def test_just_suffix(self):
        assert 'test' == remove_suffix('testing', 'ing')

    # A matching string not as suffix should produce no modifications
    def test_no_modific(self):
        assert 'testa' == remove_suffix('testa', 'test')


class TestRemoveExtension(object):
    # Removing a suffix from a filename with no extension returns the filename.
    def test_no_extension(self):
        assert 'file' == remove_file_extension('file')
        
    # A filename with two extensions should have only the first removed.
    def test_two_extensions(self):
        assert 'file.1' == remove_file_extension('file.1.2')
        
    # Standard case - remove an extension
    def test_remove_ext(self):
        assert 'file' == remove_file_extension('file.1')
        
    # Unix-style .files are not treated as extensions
    def test_unixstyle_not_ext(self):
        assert '.file' == remove_file_extension('.file')
        
    # Unix-style .file.ext works
    def test_unixstyle_ext(self):
        assert '.file' == remove_file_extension('.file.1')

    # Unix-style .file.ext works
    def test_unixstyle_path(self):
        assert '/a/b/c' == remove_file_extension('/a/b/c')
        assert '/a/b/c' == remove_file_extension('/a/b/c.1')

    # Windows-style .file.ext works
    def test_win32style_path(self):
        assert 'C:\\a\\b\\c' == remove_file_extension('C:\\a\\b\\c')
        assert 'C:\\a\\b\\c' == remove_file_extension('C:\\a\\b\\c.1')


# The name of the hookutils test files directory
TEST_MOD = 'hookutils_files'


@pytest.fixture
def mod_list(monkeypatch):
    # Add path with 'hookutils_files' module to PYTHONPATH so tests
    # could find this module - useful for subprocesses.
    pth = os.path.dirname(os.path.abspath(__file__))
    monkeypatch.setenv('PYTHONPATH', pth)
    # Use the hookutils_test_files package for testing.
    return collect_submodules(TEST_MOD)


# An error should be thrown if a module, not a package, was passed.
def test_collect_submod_module():
    # os is a module, not a package.
    with pytest.raises(ValueError):
        collect_submodules(__import__('os'))


# The package name itself should be in the returned list
def test_collect_submod_itself(mod_list):
    assert TEST_MOD in mod_list


# Python extension is included in the list.
def test_collect_submod_pyextension(mod_list):
    assert TEST_MOD + '.pyextension' in mod_list


# Check that all packages get included
def test_collect_submod_all_included(mod_list):
    mod_list.sort()
    print(mod_list)
    assert mod_list == [TEST_MOD,
                        # Python extensions on Windows ends with '.pyd' and
                        # '.so' on Linux, Mac OS X and other operating systems.
                        TEST_MOD + '.pyextension',
                        TEST_MOD + '.subpkg',
                        TEST_MOD + '.subpkg.twelve',
                        TEST_MOD + '.two']


# Dynamic libraries (.dll, .dylib) are not included in the list.
def test_collect_submod_no_dynamiclib(mod_list):
    assert TEST_MOD + '.dynamiclib' not in mod_list


# Subpackages without an __init__.py should not be included
def test_collect_submod_subpkg_init(mod_list):
    assert TEST_MOD + '.py_files_not_in_package.sub_pkg.three' not in mod_list


# Test with a subpackage
def test_collect_submod_subpkg(mod_list):
    mod_list = collect_submodules(TEST_MOD + '.subpkg')
    mod_list.sort()
    assert mod_list == [TEST_MOD + '.subpkg',
                        TEST_MOD + '.subpkg.twelve']


_DATA_BASEPATH = join(os.path.dirname(os.path.abspath(__file__)), TEST_MOD)
_DATA_PARAMS = [
    (TEST_MOD, ('dynamiclib.dll',
                'dynamiclib.dylib',
                'nine.dat',
                join('py_files_not_in_package', 'data', 'eleven.dat'),
                join('py_files_not_in_package', 'ten.dat'),
                join('subpkg', 'thirteen.txt'),
    )),
    (TEST_MOD + '.subpkg', (
                join('subpkg', 'thirteen.txt'),
    ))
]


@pytest.fixture(params=_DATA_PARAMS, ids=['package', 'subpackage'])
def data_lists(monkeypatch, request):
    def _sort(sequence):
        l = list(sequence)
        l.sort()
        return tuple(l)
    # Add path with 'hookutils_files' module to PYTHONPATH so tests
    # could find this module - useful for subprocesses.
    pth = os.path.dirname(os.path.abspath(__file__))
    monkeypatch.setenv('PYTHONPATH', pth)
    # Use the hookutils_test_files package for testing.
    mod_name = request.param[0]
    data = collect_data_files(mod_name)
    # Break list of (source, dest) into source and dest lists.
    subfiles = request.param[1]
    src = [item[0] for item in data]
    dst = [item[1] for item in data]

    return subfiles, _sort(src), _sort(dst)


# An error should be thrown if a module, not a package, was passed.
def test_collect_data_module():
    # 'os' is a module, not a package.
    with pytest.raises(ValueError):
        collect_data_files(__import__('os'))


# Make sure only data files are found.
def test_collect_data_no_extensions(data_lists):
    subfiles, src, dst = data_lists
    for item in ['pyextension.pyd', 'pyextension.so']:
        item = join(_DATA_BASEPATH, item)
        assert item not in src


# Make sure all data files are found.
def test_collect_data_all_included(data_lists):
    subfiles, src, dst = data_lists
    # Check the source and dest lists against the correct values in
    # subfiles.
    src_compare = tuple([join(_DATA_BASEPATH, subpath) for subpath in subfiles])
    dst_compare = [os.path.dirname(join(TEST_MOD, subpath)) for subpath in subfiles]
    dst_compare.sort()
    dst_compare = tuple(dst_compare)
    assert src == src_compare
    assert dst == dst_compare


# An Import error should be thrown if a module is not found.
def test_get_module_file_attribute_non_exist_module():
    with pytest.raises(ImportError):
        get_module_file_attribute('pyinst_nonexisting_module_name')
