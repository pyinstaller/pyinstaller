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
import unittest


# The function to test
from PyInstaller.utils.hooks.hookutils import remove_prefix
class TestRemovePrefix(unittest.TestCase):
    # Verify that removing a prefix from an empty string is OK.
    def test_0(self):
        self.assertEqual("", remove_prefix("", "prefix"))

    # An empty prefix should pass the string through unmodified.
    def test_1(self):
        self.assertEqual("test", remove_prefix("test", ""))

    # If the string is the prefix, it should be empty at exit.
    def test_2(self):
        self.assertEqual("", remove_prefix("test", "test"))

    # Just the prefix should be removed.
    def test_3(self):
        self.assertEqual("ing", remove_prefix("testing", "test"))

    # A matching string not as prefix should produce no modifications
    def test_4(self):
        self.assertEqual("atest", remove_prefix("atest", "test"))

# The function to test
from PyInstaller.utils.hooks.hookutils import remove_suffix
class TestRemoveSuffix(unittest.TestCase):
    # Verify that removing a suffix from an empty string is OK.
    def test_0(self):
        self.assertEqual("", remove_suffix("", "suffix"))

    # An empty suffix should pass the string through unmodified.
    def test_1(self):
        self.assertEqual("test", remove_suffix("test", ""))

    # If the string is the suffix, it should be empty at exit.
    def test_2(self):
        self.assertEqual("", remove_suffix("test", "test"))

    # Just the suffix should be removed.
    def test_3(self):
        self.assertEqual("test", remove_suffix("testing", "ing"))

    # A matching string not as suffix should produce no modifications
    def test_4(self):
        self.assertEqual("testa", remove_suffix("testa", "test"))

# The function to test
from PyInstaller.utils.hooks.hookutils import remove_file_extension
class TestRemoveExtension(unittest.TestCase):
    # Removing a suffix from a filename with no extension returns the
    # filename.
    def test_0(self):
        self.assertEqual("file", remove_file_extension("file"))
        
    # A filename with two extensions should have only the first removed.
    def test_1(self):
        self.assertEqual("file.1", remove_file_extension("file.1.2"))
        
    # Standard case - remove an extension
    def test_2(self):
        self.assertEqual("file", remove_file_extension("file.1"))
        
    # Unix-style .files are not treated as extensions
    def test_3(self):
        self.assertEqual(".file", remove_file_extension(".file"))
        
    # Unix-style .file.ext works
    def test_4(self):
        self.assertEqual(".file", remove_file_extension(".file.1"))

    # Unix-style .file.ext works
    def test_5(self):
        self.assertEqual("/a/b/c", remove_file_extension("/a/b/c.1"))


# The function to test
from PyInstaller.utils.hooks.hookutils import collect_submodules

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
    with pytest.raises(AssertionError):
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


# The function to test
from PyInstaller.utils.hooks.hookutils import collect_data_files
from os.path import join
class TestCollectDataFiles(unittest.TestCase):
    # Use the hookutils_test_files package for testing.
    def setUp(self, package = TEST_MOD):
        self.basepath = join(os.getcwd(), TEST_MOD)
        # Fun Python behavior: __import__('mod.submod') returns mod,
        # where as __import__('mod.submod', fromlist = [a non-empty list])
        # returns mod.submod. See the docs on `__import__
        # <http://docs.python.org/library/functions.html#__import__>`_.
        self.data_list = collect_data_files(__import__(package,
                                                      fromlist = ['']))
        self.split_data_list()

    # Break list of (source, dest) inst source and dest lists
    def split_data_list(self):
        self.source_list = [item[0] for item in self.data_list]
        self.dest_list = [item[1] for item in self.data_list]

    # An error should be thrown if a module, not a package, was passed.
    def test_0(self):
        # os is a module, not a package.
        with self.assertRaises(AttributeError):
            collect_data_files(__import__('os'))

    # Check the source and dest lists against the correct values in
    # subfiles.
    def assert_data_list_equal(self, subfiles):
        self.assertSequenceEqual(self.source_list,
          [join(self.basepath, subpath) for subpath in subfiles])
        self.assertSequenceEqual(self.dest_list,
          [os.path.dirname(join(TEST_MOD, subpath))
          for subpath in subfiles])

    # Make sure only data files are found
    all_subfiles = ('nine.dat',
                    'six.dll',
                    join('py_files_not_in_package', 'ten.dat'),
                    join('py_files_not_in_package', 'data', 'eleven.dat'),
                    join('subpkg', 'thirteen.txt'),
                   )
    def test_1(self):
        self.assert_data_list_equal(self.all_subfiles)

    # Test with a subpackage
    subpkg_subfiles = (join('subpkg', 'thirteen.txt'), )
    def test_2(self):
        self.setUp(TEST_MOD + '.subpkg')
        self.assert_data_list_equal(self.subpkg_subfiles)

    # Test with a string package name
    def test_3(self):
        self.data_list = collect_data_files(TEST_MOD)
        self.split_data_list()
        self.assert_data_list_equal(self.all_subfiles)

    # Test with a string package name
    def test_4(self):
        self.data_list = collect_data_files(TEST_MOD +
                                            '.subpkg')
        self.split_data_list()
        self.assert_data_list_equal(self.subpkg_subfiles)
