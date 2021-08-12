#-----------------------------------------------------------------------------
# Copyright (c) 2005-2021, PyInstaller Development Team.
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
import pathlib
import shutil
from os.path import join

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, \
    get_module_file_attribute, remove_prefix, remove_suffix, \
    remove_file_extension, is_module_or_submodule, \
    is_module_satisfies, _copy_metadata_dest
from PyInstaller.compat import exec_python, is_win


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
TEST_MOD = 'hookutils_package'
# The path to this directory.
TEST_MOD_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hookutils_files')


@pytest.fixture
def mod_list(monkeypatch):
    # Add 'hookutils_files' to sys.path (so ``is_package`` can find it) and to
    # ``pathex`` (so code run in a subprocess can find it).
    monkeypatch.setattr('PyInstaller.config.CONF', {'pathex': [TEST_MOD_PATH]})
    monkeypatch.syspath_prepend(TEST_MOD_PATH)
    # Use the hookutils_test_files package for testing.
    return collect_submodules(TEST_MOD)


class TestCollectSubmodules(object):
    # An error should be thrown if a module, not a package, was passed.
    def test_collect_submod_module(self):
        # os is a module, not a package.
        with pytest.raises(TypeError):
            collect_submodules(__import__('os'))

    # The package name itself should be in the returned list.
    def test_collect_submod_itself(self, mod_list):
        assert TEST_MOD in mod_list

    # Python extension is included in the list.
    def test_collect_submod_pyextension(self, mod_list):
        assert TEST_MOD + '.pyextension' in mod_list

    # Check that all packages get included
    def test_collect_submod_all_included(self, mod_list):
        mod_list.sort()
        assert mod_list == [
            TEST_MOD,
            # Python extensions end with '.pyd' on Windows and with  '.so' on Linux, Mac OS, and other OSes.
            TEST_MOD + '.pyextension',
            TEST_MOD + '.subpkg',
            TEST_MOD + '.subpkg.twelve',
            TEST_MOD + '.two'
        ]

    # Dynamic libraries (.dll, .dylib) are not included in the list.
    def test_collect_submod_no_dynamiclib(self, mod_list):
        assert TEST_MOD + '.dynamiclib' not in mod_list

    # Subpackages without an __init__.py should not be included.
    def test_collect_submod_subpkg_init(self, mod_list):
        assert TEST_MOD + '.py_files_not_in_package.sub_pkg.three' not in mod_list

    # Test with a subpackage.
    def test_collect_submod_subpkg(self, mod_list):
        # Note: Even though mod_list is overwritten, it is still needed as a fixture, so that the path to the
        # TEST_MOD is set correctly.
        mod_list = collect_submodules(TEST_MOD + '.subpkg')
        mod_list.sort()
        assert mod_list == [TEST_MOD + '.subpkg', TEST_MOD + '.subpkg.twelve']

    # Test in an ``.egg`` file.
    def test_collect_submod_egg(self, tmpdir, monkeypatch):
        # Copy files to a tmpdir for egg building.
        dest_path = tmpdir.join('hookutils_package')
        shutil.copytree(TEST_MOD_PATH, dest_path.strpath)
        monkeypatch.chdir(dest_path)

        # Create an egg from the test package. For debug, show the output of the egg build.
        print(exec_python('setup.py', 'bdist_egg'))

        # Obtain the name of the egg, which depends on the Python version.
        dist_path = dest_path.join('dist')
        fl = os.listdir(dist_path.strpath)
        assert len(fl) == 1
        egg_name = fl[0]
        assert egg_name.endswith('.egg')

        # Add the egg to Python's path.
        pth = dist_path.join(egg_name).strpath
        monkeypatch.setattr('PyInstaller.config.CONF', {'pathex': [pth]})
        monkeypatch.syspath_prepend(pth)

        # Verify its contents.
        ml = collect_submodules(TEST_MOD)
        self.test_collect_submod_all_included(ml)

    # Messages printed to stdout by modules during collect_submodules() should not affect the collected modules list.
    def test_collect_submod_stdout_interference(self, monkeypatch):
        TEST_MOD = 'foo'
        TEST_MOD_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hookutils_files2')

        monkeypatch.setattr('PyInstaller.config.CONF', {'pathex': [TEST_MOD_PATH]})
        monkeypatch.syspath_prepend(TEST_MOD_PATH)

        ml = collect_submodules(TEST_MOD)
        ml = sorted(ml)

        assert ml == ['foo', 'foo.bar']


def test_is_module_or_submodule():
    assert is_module_or_submodule('foo.bar', 'foo.bar')
    assert is_module_or_submodule('foo.bar.baz', 'foo.bar')
    assert not is_module_or_submodule('foo.bard', 'foo.bar')
    assert not is_module_or_submodule('foo', 'foo.bar')


def test_is_module_satisfies_package_not_installed():
    assert is_module_satisfies('pytest')
    assert not is_module_satisfies('magnumopus-no-package-test-case')


# An error should be raised if a module, not a package, was passed.
def test_collect_data_module():
    # 'os' is a module, not a package.
    with pytest.raises(TypeError):
        collect_data_files(__import__('os'))


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
                join('py_files_not_in_package', 'data', 'eleven.dat'),
                join('py_files_not_in_package', 'ten.dat'),
                # Not backwards! On Windows, ``.so`` files are just data and vice versa.
                'pyextension.so' if is_win else 'pyextension.pyd',
                join('subpkg', 'thirteen.txt'),
            )
        ),
        # Test collecting from a subpackage.
        ([TEST_MOD + '.subpkg'], {}, (join('subpkg', 'thirteen.txt'),)),
        ([TEST_MOD], dict(include_py_files=True, excludes=['**/__pycache__']), (
            '__init__.py',
            'dynamiclib.dll',
            'dynamiclib.dylib',
            'nine.dat',
            join('py_files_not_in_package', 'data', 'eleven.dat'),
            join('py_files_not_in_package', 'one.py'),
            join('py_files_not_in_package', 'sub_pkg', '__init__.py'),
            join('py_files_not_in_package', 'sub_pkg', 'three.py'),
            join('py_files_not_in_package', 'ten.dat'),
            'pyextension.pyd',
            'pyextension.so',
            join('subpkg', '__init__.py'),
            join('subpkg', 'thirteen.txt'),
            join('subpkg', 'twelve.py'),
            'two.py',
        )),
        ([TEST_MOD], dict(excludes=['py_files_not_in_package', '**/__pycache__']), (
            'dynamiclib.dll',
            'dynamiclib.dylib',
            'nine.dat',
            'pyextension.so' if is_win else 'pyextension.pyd',
            join('subpkg', 'thirteen.txt'),
        )),
        ([TEST_MOD], dict(includes=['**/*.dat', '**/*.txt']), (
            'nine.dat',
            join('py_files_not_in_package', 'data', 'eleven.dat'),
            join('py_files_not_in_package', 'ten.dat'),
            join('subpkg', 'thirteen.txt'),
        )),
        ([TEST_MOD], dict(includes=['*.dat']), ('nine.dat',)),
        ([TEST_MOD], dict(subdir="py_files_not_in_package", excludes=['**/__pycache__']), (
            join('py_files_not_in_package', 'data', 'eleven.dat'),
            join('py_files_not_in_package', 'ten.dat'),
        )),
    ],  # yapf: disable
    ids=['package', 'subpackage', 'package with py files', 'excludes', '** includes', 'includes', 'subdir']
)
def data_lists(monkeypatch, request):
    def _sort(sequence):
        sorted_list = sorted(list(sequence))
        return tuple(sorted_list)

    # Add path with 'hookutils_files' module to ``sys.path``, so tests can find this module - useful for subprocesses.
    monkeypatch.syspath_prepend(TEST_MOD_PATH)
    # Use the hookutils_test_files package for testing.
    args, kwargs, subfiles = request.param
    data = collect_data_files(*args, **kwargs)
    # Break list of (source, dest) into source and dest lists.
    src = [item[0] for item in data]
    dst = [item[1] for item in data]

    return subfiles, _sort(src), _sort(dst)


# Make sure the correct files are found.
def test_collect_data_all_included(data_lists):
    subfiles, src, dst = data_lists
    # Check the source and dest lists against the correct values in subfiles.
    src_compare = tuple([join(TEST_MOD_PATH, TEST_MOD, subpath) for subpath in subfiles])
    dst_compare = [os.path.dirname(join(TEST_MOD, subpath)) for subpath in subfiles]
    dst_compare.sort()
    dst_compare = tuple(dst_compare)
    assert src == src_compare
    assert dst == dst_compare


# An ImportError should be raised if the module is not found.
def test_get_module_file_attribute_non_exist_module():
    with pytest.raises(ImportError):
        get_module_file_attribute('pyinst_nonexisting_module_name')


@pytest.mark.parametrize("egg_path,name,target", [
    # Something installed via `pip install -e .`.
    ("editable/install/CodeChat.egg-info",
     "CodeChat", "CodeChat.egg-info"),
    # An egg distribution - it's unlikely we'll ever see these now.
    ("lib/site-packages/pypubsub-3.3.0-py2.7.egg/EGG-INFO",
     "pypubsub", "pypubsub-3.3.0-py2.7.egg/EGG-INFO"),
    # A classic wheel-installed distribution.
    ("lib/site-packages/zest.releaser-6.2.dist-info",
     "zest.releaser", "zest.releaser-6.2.dist-info"),
    # Must be tolerant to case and -/_ mismatch.
    ("/site-packages/importlib_metadata-4.0.1.dist-info",
     "ImPorTlib-mEtADatA", "importlib_metadata-4.0.1.dist-info")
])  # yapf: disable
def test_copy_metadata_dest(egg_path, name, target):
    """
    Test choosing dest path for copy_metadata() across distribution types.
    """
    # Convert posix style filenames to native paths, i.e. replace '/' with '\' on Windows.
    egg_path = str(pathlib.PurePath(egg_path))
    target = str(pathlib.PurePath(target))

    assert _copy_metadata_dest(egg_path, name) == target


def test_erroneous_distribution_type():
    with pytest.raises(RuntimeError, match="Unknown .* type 'foo' from the " "'bar' distribution"):
        _copy_metadata_dest("foo", "bar")
    with pytest.raises(RuntimeError, match=r"No .* distribution 'foo'\."):
        _copy_metadata_dest(None, "foo")
