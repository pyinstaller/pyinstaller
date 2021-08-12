#-----------------------------------------------------------------------------
# Copyright (c) 2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
#
# A test script for validation of pkg_resources provider implementation.
#
# The test package has the following structure:
#
# pyi_pkgres_testpkg/
# ├── a.py
# ├── b.py
# ├── __init__.py
# ├── subpkg1
# │   ├── c.py
# │   ├── data
# │   │   ├── entry1.txt
# │   │   ├── entry2.md
# │   │   ├── entry3.rst
# │   │   └── extra
# │   │       └── extra_entry1.json
# │   ├── d.py
# │   └── __init__.py
# ├── subpkg2
# │   ├── __init__.py
# │   ├── mod.py
# │   └── subsubpkg21
# │       ├── __init__.py
# │       └── mod.py
# └── subpkg3
#     ├── _datafile.json
#     └── __init__.py
#
# When run as unfrozen script, this script can be used to check the behavior of "native" providers that come with
# pkg_resources, such as DefaultProvider (for regular packages) and ZipProvider (for eggs).
#
# When run as a frozen application, this script validates the behavior of the frozen provider implemented by
# PyInstaller. Due to transitivity of test results, this script running without errors both as a native script and
# as a frozen application serves as proof of conformance for the PyInstaller's provider.
#
# Wherever the behavior between the native providers is inconsistent, we allow the same leeway for the PyInstaller's
# frozen provider.

import sys
from pkg_resources import resource_exists, resource_isdir, resource_listdir
from pkg_resources import get_provider, DefaultProvider, ZipProvider

pkgname = 'pyi_pkgres_testpkg'

# Identify provider type
provider = get_provider(pkgname)
is_default = isinstance(provider, DefaultProvider)
is_zip = isinstance(provider, ZipProvider)
is_frozen = getattr(sys, 'frozen', False)

assert is_default or is_zip or is_frozen, "Unsupported provider type!"

########################################################################
#                Validate behavior of resource_exists()                #
########################################################################
# Package's directory
#  * DefaultProvider returns True
#  * ZipProvider returns False
#  > PyiFrozenProvider returns True
ret = resource_exists(pkgname, '.')
assert (is_default and ret) or \
       (is_zip and not ret) or \
       (is_frozen and ret)

# Package's directory, with empty path
assert resource_exists(pkgname, '')

# Subpackage's directory (relative to main package):
assert resource_exists(pkgname, 'subpkg1')
assert resource_exists(pkgname, 'subpkg2')
assert resource_exists(pkgname, 'subpkg2/subsubpkg21')
assert resource_exists(pkgname, 'subpkg3')

# Subpackage's directory (relative to subpackage itself):
#  * DefaultProvider returns True
#  * ZipProvider returns False
#  > PyiFrozenProvider returns True
ret = resource_exists(pkgname + '.subpkg1', '.')
assert (is_default and ret) or \
       (is_zip and not ret) or \
       (is_frozen and ret)

# Subpackage's directory (relative to subpackage itself), with empty path:
assert resource_exists(pkgname + '.subpkg1', '')

# Data directory in subpackage
assert resource_exists(pkgname, 'subpkg1/data')
assert resource_exists(pkgname + '.subpkg1', 'data')

# Subdirectory in data directory
assert resource_exists(pkgname, 'subpkg1/data/extra')
assert resource_exists(pkgname + '.subpkg1', 'data/extra')

# File in data directory
assert resource_exists(pkgname, 'subpkg1/data/entry1.txt')

# Deeply nested data file
assert resource_exists(pkgname, 'subpkg1/data/extra/extra_entry1.json')

# A non-existant file/directory - should return False
assert not resource_exists(pkgname, 'subpkg1/non-existant')

# A source script file in package
#  > PyiFrozenProvider returns False because frozen application does not contain source files
ret = resource_exists(pkgname, '__init__.py')
assert (not is_frozen and ret) or \
       (is_frozen and not ret)

# Parent of pacakge's top-level directory
#  * DefaultProvider returns True
#  * ZipProvider returns False
#  > PyiFrozenProvider disallows jumping to parent, and returns False
# NOTE: using .. in path is deprecated (since setuptools 40.8.0) and will raise exception in a future release.
ret = resource_exists(pkgname, '..')
assert (is_default and ret) or \
       (is_zip and not ret) or \
       (is_frozen and not ret)

# Parent of subpackage's directory
#  * DefaultProvider returns True
#  * ZipProvider returns False
#  > PyiFrozenProvider disallows jumping to parent, and returns False
# NOTE: using .. in path is deprecated (since setuptools 40.8.0) and will raise exception in a future release.
ret = resource_exists(pkgname + '.subpkg1', '..')
assert (is_default and ret) or \
       (is_zip and not ret) or \
       (is_frozen and not ret)

# Submodule in main package
ret = resource_exists(pkgname + '.a', '.')
assert (is_default and ret) or \
       (is_zip and not ret) or \
       (is_frozen and ret)

# Submodule in main package, with empty path
assert resource_exists(pkgname + '.a', '')

# Submodule in subpackage
ret = resource_exists(pkgname + '.subpkg1.c', '.')
assert (is_default and ret) or \
       (is_zip and not ret) or \
       (is_frozen and ret)

# Submodule in subpackage, with empty path
assert resource_exists(pkgname + '.subpkg1.c', '')

########################################################################
#                Validate behavior of resource_isdir()                 #
########################################################################
# Package's directory
#  * DefaultProvider returns True
#  * ZipProvider returns False
#  > PyiFrozenProvider returns True
ret = resource_isdir(pkgname, '.')
assert (is_default and ret) or \
       (is_zip and not ret) or \
       (is_frozen and ret)

# Package's directory, with empty path
assert resource_isdir(pkgname, '')

# Subpackage's directory (relative to main pacakge):
#  * both DefaultProvider and ZipProvider return True
assert resource_isdir(pkgname, 'subpkg1')
assert resource_isdir(pkgname, 'subpkg2')
assert resource_isdir(pkgname, 'subpkg2/subsubpkg21')
assert resource_isdir(pkgname, 'subpkg3')

# Subpackage's directory (relative to subpackage itself):
#  * DefaultProvider returns True
#  * ZipProvider returns False
#  > PyiFrozenProvider returns True
ret = resource_isdir(pkgname + '.subpkg1', '.')
assert (is_default and ret) or \
       (is_zip and not ret) or \
       (is_frozen and ret)

# Subpackage's directory (relative to subpackage itself), with empty path:
assert resource_isdir(pkgname + '.subpkg1', '')

# Data directory in subpackage
assert resource_isdir(pkgname, 'subpkg1/data')
assert resource_isdir(pkgname + '.subpkg1', 'data')

# Subdirectory in data directory
assert resource_isdir(pkgname, 'subpkg1/data/extra')
assert resource_isdir(pkgname + '.subpkg1', 'data/extra')

# File in data directory - should return False
assert not resource_isdir(pkgname, 'subpkg1/data/entry1.txt')

# Deeply nested data file - should return False
assert not resource_isdir(pkgname, 'subpkg1/data/extra/extra_entry1.json')

# A non-existant file-directory - should return False
assert not resource_isdir(pkgname, 'subpkg1/non-existant')

# A source script file in package - should return False
# NOTE: PyFrozenProvider returns False because the file does not exist.
assert not resource_isdir(pkgname, '__init__.py')

# Parent of package's top-level directory
#  * DefaultProvider returns True
#  * ZipProvider returns False
#  > PyiFrozenProvider disallows jumping to parent, and returns False
# NOTE: using .. in path is deprecated (since setuptools 40.8.0) and will raise exception in a future release.
ret = resource_isdir(pkgname, '..')
assert (is_default and ret) or \
       (is_zip and not ret) or \
       (is_frozen and not ret)

# Parent of subpacakge's directory
#  * DefaultProvider returns True
#  * ZipProvider returns False
#  > PyiFrozenProvider disallows jumping to parent, and returns False
# NOTE: using .. in path is deprecated (since setuptools 40.8.0) and will raise exception in a future release.
ret = resource_isdir(pkgname + '.subpkg1', '..')
assert (is_default and ret) or \
       (is_zip and not ret) or \
       (is_frozen and not ret)

# Submodule in main package
ret = resource_isdir(pkgname + '.a', '.')
assert (is_default and ret) or \
       (is_zip and not ret) or \
       (is_frozen and ret)

# Submodule in main package, with empty path
assert resource_isdir(pkgname + '.a', '')

# Submodule in subpackage
ret = resource_isdir(pkgname + '.subpkg1.c', '.')
assert (is_default and ret) or \
       (is_zip and not ret) or \
       (is_frozen and ret)

# Submodule in subpackage, with empty path
assert resource_isdir(pkgname + '.subpkg1.c', '')


########################################################################
#               Validate behavior of resource_listdir()                #
########################################################################
# A helper for resource_listdir() tests.
def _listdir_test(pkgname, path, expected):
    # For frozen application, remove .py files from expected results
    if is_frozen:
        expected = [x for x in expected if not x.endswith('.py')]
    # List the content
    content = resource_listdir(pkgname, path)
    # Ignore pycache
    if '__pycache__' in content:
        content.remove('__pycache__')
    assert sorted(content) == sorted(expected)


# List package's top-level directory
#  * DefaultProvider lists the directory
#  * ZipProvider returns empty list
#  > PyiFrozenProvider lists the directory, but does not provide source .py files
if is_zip:
    expected = []
else:
    expected = ['__init__.py', 'a.py', 'b.py', 'subpkg1', 'subpkg2', 'subpkg3']
_listdir_test(pkgname, '.', expected)

# List package's top-level directory, with empty path
#  > PyiFrozenProvider lists the directory, but does not provide source .py files
expected = ['__init__.py', 'a.py', 'b.py', 'subpkg1', 'subpkg2', 'subpkg3']
_listdir_test(pkgname, '', expected)

# List subpackage's directory (relative to main package)
#  > PyiFrozenProvider lists the directory, but does not provide source .py files
expected = ['__init__.py', 'c.py', 'd.py', 'data']
_listdir_test(pkgname, 'subpkg1', expected)

# List data directory in subpackage (relative to main package)
expected = ['entry1.txt', 'entry2.md', 'entry3.rst', 'extra']
_listdir_test(pkgname, 'subpkg1/data', expected)

# List data directory in subpackage (relative to subpackage itself)
expected = ['entry1.txt', 'entry2.md', 'entry3.rst', 'extra']
_listdir_test(pkgname + '.subpkg1', 'data', expected)

# List data in subdirectory of data directory in subpackage
expected = ['extra_entry1.json']
_listdir_test(pkgname + '.subpkg1', 'data/extra', expected)

# Attempt to list a file (existing resource but not a directory).
#  * DefaultProvider raises NotADirectoryError
#  * ZipProvider returns empty list
#  > PyiFrozenProvider returns empty list
try:
    content = resource_listdir(pkgname + '.subpkg1', 'data/entry1.txt')
except NotADirectoryError:
    assert is_default
except Exception:
    raise
else:
    assert (is_zip or is_frozen) and content == []

# Attempt to list an non-existant directory in main package.
#  * DefaultProvider raises FileNotFoundError
#  * ZipProvider returns empty list
#  > PyiFrozenProvider returns empty list
try:
    content = resource_listdir(pkgname, 'non-existant')
except FileNotFoundError:
    assert is_default
except Exception:
    raise
else:
    assert (is_zip or is_frozen) and content == []

# Attempt to list an non-existant directory in subpackage
#  * DefaultProvider raises FileNotFoundError
#  * ZipProvider returns empty list
#  > PyiFrozenProvider returns empty list
try:
    content = resource_listdir(pkgname + '.subpkg1', 'data/non-existant')
except FileNotFoundError:
    assert is_default
except Exception:
    raise
else:
    assert (is_zip or is_frozen) and content == []

# Attempt to list pacakge's parent directory
#  * DefaultProvider actually lists the parent directory
#  * ZipProvider returns empty list
#  > PyiFrozenProvider disallows jumping to parent, and returns empty list
# NOTE: using .. in path is deprecated (since setuptools 40.8.0) and
# will raise exception in a future release
content = resource_listdir(pkgname, '..')
assert (is_default and pkgname in content) or \
       (is_zip and content == []) or \
       (is_frozen and content == [])

# Attempt to list subpackage's parent directory
#  * DefaultProvider actually lists the parent directory
#  * ZipProvider returns empty list
#  > PyiFrozenProvider disallows jumping to parent, and returns False
# NOTE: using .. in path is deprecated (since setuptools 40.8.0) and will raise exception in a future release.
if is_default:
    expected = ['__init__.py', 'a.py', 'b.py', 'subpkg1', 'subpkg2', 'subpkg3']
else:
    expected = []
_listdir_test(pkgname + '.subpkg1', '..', expected)

# Attempt to list directory of subpackage that has no data files or directories (relative to main package)
expected = ['__init__.py', 'mod.py', 'subsubpkg21']
_listdir_test(pkgname, 'subpkg2', expected)

# Attempt to list directory of subpackage that has no data files or directories (relative to subpackage itself)
expected = ['__init__.py', 'mod.py', 'subsubpkg21']
_listdir_test(pkgname + '.subpkg2', '', expected)  # empty path!

# Attempt to list directory of subsubpackage that has no data files/directories (relative to main package)
expected = ['__init__.py', 'mod.py']
_listdir_test(pkgname, 'subpkg2/subsubpkg21', expected)

# Attempt to list directory of subsubpackage that has no data files/directories (relative to parent subpackage)
expected = ['__init__.py', 'mod.py']
_listdir_test(pkgname + '.subpkg2', 'subsubpkg21', expected)

# Attempt to list directory of subsubpackage that has no data files/directories (relative to subsubpackage itself)
expected = ['__init__.py', 'mod.py']
_listdir_test(pkgname + '.subpkg2.subsubpkg21', '', expected)  # empty path!

# Attempt to list submodule in main package - should give the same results as listing the package itself
assert sorted(resource_listdir(pkgname + '.a', '')) == \
       sorted(resource_listdir(pkgname, ''))  # empty path!

# Attempt to list submodule in subpackage - should give the same results as listing the subpackage itself
assert sorted(resource_listdir(pkgname + '.subpkg1.c', '')) == \
       sorted(resource_listdir(pkgname + '.subpkg1', ''))  # empty path!
