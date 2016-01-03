#-----------------------------------------------------------------------------
# Copyright (c) 2005-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# This contains tests for the class:``Tree``, see
# https://pythonhosted.org/PyInstaller/#the-tree-class

import os
import pytest

from os.path import join
import PyInstaller.building.datastruct


class Tree(PyInstaller.building.datastruct.Tree):
    # A stripped-down version of PyInstaller.building.datastruct.Tree,
    # not checking guts, but only the `assemble()` step
    def __postinit__(self):
        self.assemble()


TEST_MOD = 'Tree_files'
_DATA_BASEPATH = join(os.path.dirname(os.path.abspath(__file__)), TEST_MOD)

_TEST_FILES = sorted([
    join('subpkg', 'twelve.py'),
    join('subpkg', 'thirteen.txt'),
    join('subpkg', 'init__.py'),
    'two.py',
    'dynamiclib.dylib',
    join('py_files_not_in_package', 'sub_pkg', 'three.py'),
    join('py_files_not_in_package', 'sub_pkg', 'init__.py'),
    join('py_files_not_in_package', 'one.py'),
    join('py_files_not_in_package', 'data', 'eleven.dat'),
    join('py_files_not_in_package', 'ten.dat'),
    'dynamiclib.dll',
    'pyextension.pyd',
    'nine.dat',
    'init__.py',
    'pyextension.so',
])

_PARAMETERS = (
    (None, None, _TEST_FILES),
    ('abc', None, [join('abc', f) for f in _TEST_FILES]),
    (None, ['*.py'], 
     [f for f in _TEST_FILES if not f.endswith('.py')]),
    (None, ['*.py', '*.pyd'], 
     [f for f in _TEST_FILES if not f.endswith(('.py', '.pyd'))]),
    (None, ['subpkg'], 
     [f for f in _TEST_FILES 
      if not f.startswith('subpkg')]),
    (None, ['subpkg', 'sub_pkg'],
     [f for f in _TEST_FILES 
      if not (f.startswith('subpkg') or os.sep+'sub_pkg'+os.sep in f)]),
    ('klm', ['subpkg', 'sub_pkg', '*.py', '*.pyd'],
     [join('klm', f) for f in _TEST_FILES 
      if not (f.startswith('subpkg') or os.sep+'sub_pkg'+os.sep in f or
              f.endswith(('.py', '.pyd')))]),
)

@pytest.mark.parametrize("prefix,excludes,result", _PARAMETERS)
def test_Tree(monkeypatch, prefix, excludes, result):
    monkeypatch.setattr('PyInstaller.config.CONF', {'workpath': '.'})
    tree = Tree(_DATA_BASEPATH, prefix=prefix, excludes=excludes)
    files = sorted(f[0] for f in tree)
    assert files == sorted(result)
