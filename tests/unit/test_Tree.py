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
import PyInstaller.building.datastruct


class Tree(PyInstaller.building.datastruct.Tree):
    # A stripped-down version of PyInstaller.building.datastruct.Tree,
    # not checking guts, but only the `assemble()` step
    def __init__(self, root=None, prefix=None, excludes=None):
        self.root = root
        self.prefix = prefix
        self.excludes = excludes or []
        self.tocbasename = ''
        self.assemble()

# Reuse the hookutils test files directory
TEST_MOD = 'hookutils_files'
_DATA_BASEPATH = join(os.path.dirname(os.path.abspath(__file__)), TEST_MOD)
# :todo: This will fail if some ``__pychace__`` file exists for any
# reason
_TEST_FILES = sorted([
    'subpkg/twelve.py',
    'subpkg/thirteen.txt',
    'subpkg/__init__.py',
    'two.py',
    'dynamiclib.dylib',
    'py_files_not_in_package/sub_pkg/three.py',
    'py_files_not_in_package/sub_pkg/__init__.py',
    'py_files_not_in_package/one.py',
    'py_files_not_in_package/data/eleven.dat',
    'py_files_not_in_package/ten.dat',
    'dynamiclib.dll',
    'pyextension.pyd',
    'nine.dat',
    '__init__.py',
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
      if not (f.startswith('subpkg') or '/sub_pkg/' in f)]),
    ('klm', ['subpkg', 'sub_pkg', '*.py', '*.pyd'],
     [join('klm', f) for f in _TEST_FILES 
      if not (f.startswith('subpkg') or '/sub_pkg/' in f or 
              f.endswith(('.py', '.pyd')))]),
)

@pytest.mark.parametrize("prefix,excludes,result", _PARAMETERS)
def test_Tree(prefix, excludes, result):
    tree = Tree(_DATA_BASEPATH, prefix=prefix, excludes=excludes)
    files = sorted(f[0] for f in tree.data)
    assert files == sorted(result)
