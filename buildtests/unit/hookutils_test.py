#
# Copyright (C) 2012 Bryan A. Jones
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

# This program will execute any file with name test*<digit>.py. If your test
# need an aditional dependency name it test*<digit><letter>.py to be ignored
# by this program but be recognizable by any one as a dependency of that
# particular test.

# Copied from ../runtests.py
import os

try:
    import PyInstaller
except ImportError:
    # if importing PyInstaller fails, try to load from parent
    # directory to support running without installation
    import imp
    if not hasattr(os, "getuid") or os.getuid() != 0:
        imp.load_module('PyInstaller', *imp.find_module('PyInstaller',
            [os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))]))

# Use unittest2 with PyInstaller tweaks. See
# http://www.voidspace.org.uk/python/articles/unittest2.shtml for some
# documentation.
import PyInstaller.lib.unittest2 as unittest

# The function to test
from PyInstaller.hooks.hookutils import remove_prefix
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
from PyInstaller.hooks.hookutils import remove_suffix
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
from PyInstaller.hooks.hookutils import remove_file_extension
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

# The name of the hookutils test files directory
HOOKUTILS_TEST_FILES = 'hookutils_test_files'

# The function to test
from PyInstaller.hooks.hookutils import collect_submodules
class TestCollectSubmodules(unittest.TestCase):
    # Use the hookutils_test_files package for testing.
    def setUp(self, package = HOOKUTILS_TEST_FILES):
        # Fun Python behavior: __import__('mod.submod') returns mod,
        # where as __import__('mod.submod', fromlist = [a non-empty list])
        # returns mod.submod. See the docs on `__import__
        # <http://docs.python.org/library/functions.html#__import__>`_.
        self.mod_list = collect_submodules(__import__(package,
                                                      fromlist = ['']))

    # An error should be thrown if a module, not a package, was passed.
    def test_0(self):
        # os is a module, not a package.
        with self.assertRaises(AttributeError):
            collect_submodules(__import__('os'))

    # The package name itself should be in the returned list
    def test_1(self):
        self.assertTrue(HOOKUTILS_TEST_FILES in self.mod_list)

    # Subpackages without an __init__.py should not be included
    def test_2(self):
        self.assertTrue(HOOKUTILS_TEST_FILES +
          '.py_files_not_in_package.sub_pkg.three' not in self.mod_list)

    # Check that all packages get included
    def test_3(self):
        self.assertItemsEqual(self.mod_list, 
                              [HOOKUTILS_TEST_FILES,
                               HOOKUTILS_TEST_FILES + '.two',
                               HOOKUTILS_TEST_FILES + '.four',
                               HOOKUTILS_TEST_FILES + '.five',
                               HOOKUTILS_TEST_FILES + '.eight',
                               HOOKUTILS_TEST_FILES + '.subpkg',
                               HOOKUTILS_TEST_FILES + '.subpkg.twelve',
                              ])

    def assert_subpackge_equal(self):
        self.assertItemsEqual(self.mod_list,
                              [HOOKUTILS_TEST_FILES + '.subpkg',
                               HOOKUTILS_TEST_FILES + '.subpkg.twelve',
                              ])

    # Test with a subpackage
    def test_4(self):
        self.setUp(HOOKUTILS_TEST_FILES + '.subpkg')
        self.assert_subpackge_equal()

    # Test with a string for the package name
    def test_5(self):
        self.mod_list = collect_submodules(HOOKUTILS_TEST_FILES)
        self.test_3()

    # Test with a string for the subpackage name
    def test_6(self):
        self.mod_list = collect_submodules(HOOKUTILS_TEST_FILES +
                                           '.subpkg')
        self.assert_subpackge_equal()

# The function to test
from PyInstaller.hooks.hookutils import collect_data_files
from os.path import join
class TestCollectDataFiles(unittest.TestCase):
    # Use the hookutils_test_files package for testing.
    def setUp(self, package = HOOKUTILS_TEST_FILES):
        self.basepath = join(os.getcwd(), HOOKUTILS_TEST_FILES)
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
          [os.path.dirname(join(HOOKUTILS_TEST_FILES, subpath))
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
        self.setUp(HOOKUTILS_TEST_FILES + '.subpkg')
        self.assert_data_list_equal(self.subpkg_subfiles)

    # Test with a string package name
    def test_3(self):
        self.data_list = collect_data_files(HOOKUTILS_TEST_FILES)
        self.split_data_list()
        self.assert_data_list_equal(self.all_subfiles)

    # Test with a string package name
    def test_4(self):
        self.data_list = collect_data_files(HOOKUTILS_TEST_FILES +
                                            '.subpkg')
        self.split_data_list()
        self.assert_data_list_equal(self.subpkg_subfiles)


# Provide an easy way to run just one test for debug purposes
def one_test():
    suite = unittest.TestSuite()
    suite.addTest(TestCollectSubmodules('test_4'))
    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    unittest.main()
    #one_test()