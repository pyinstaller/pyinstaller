#-----------------------------------------------------------------------------
# Copyright (c) 2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
#
# A test script for validation of importlib.resources / importlib_resources resource reader implementation.
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
# When run as unfrozen script, this script can be used to check the behavior of "native" resource readers (or
# compatbility adapters for python-provided loaders) that are provided by importlib.resources (or its
# importlib_resources back-port for python 3.8 and earlier).
#
# When run as a frozen application, this script validates the behavior of the resource reader implemented by
# PyInstaller. Due to transitivity of test results, this script running without errors both as a native script and
# as a frozen application serves as proof of conformance for the PyInstaller's reader.
#
# NOTE: this test is modelled after pkg_resources test, but it does not support zipped eggs. Similarly, it assumes that
# in the frozen version, only access to on-disk resources is provided (either by importlib.resources's adapter, or by
# PyInstaller's custom resource reader, if/when implemented). Without custom resource reader, the frozen version of the
# test seems to work with the importlib.resources (python 3.9 and later) but not with the importlib_resources (python
# 3.8 and earlier), due to implementation differences.

import sys
import pathlib

try:
    from importlib.resources import (
        as_file as importlib_resources_as_file,
        contents as importlib_resources_contents,
        is_resource as importlib_resources_is_resource,
        files as importlib_resources_files,
        path as importlib_resources_path,
        read_binary as importlib_resources_read_binary,
        read_text as importlib_resources_read_text,
    )
    is_builtin = True
    print("Using built-in importlib.resources...")
except ImportError:
    from importlib_resources import (
        as_file as importlib_resources_as_file,
        contents as importlib_resources_contents,
        is_resource as importlib_resources_is_resource,
        files as importlib_resources_files,
        path as importlib_resources_path,
        read_binary as importlib_resources_read_binary,
        read_text as importlib_resources_read_text,
    )
    is_builtin = False
    print("Using backported importlib_resources...")

is_frozen = getattr(sys, 'frozen', False)


########################################################################
#          Validate behavior of importlib.resources.contents()         #
########################################################################
def _contents_test(pkgname, expected):
    # For frozen application, remove .py files from expected results.
    if is_frozen:
        expected = [x for x in expected if not x.endswith('.py')]
    # List the content
    content = list(importlib_resources_contents(pkgname))
    # Ignore pycache
    if '__pycache__' in content:
        content.remove('__pycache__')
    assert sorted(content) == sorted(expected), f"Content mismatch: {sorted(content)} vs. {sorted(expected)}"


# NOTE: contents() seems to be broken in importlib.resources (python 3.9) for zipped eggs, as it also recursively lists
# all subdirectories (but not their files) instead of just directories within the package directory.

# Top-level package
expected = ['__init__.py', 'a.py', 'b.py', 'subpkg1', 'subpkg2', 'subpkg3']
if is_frozen:
    expected.remove('subpkg2')  # FIXME: frozen reader does not list directories that are not on filesystem.
_contents_test('pyi_pkgres_testpkg', expected)

# Subpackage #1
expected = ['__init__.py', 'c.py', 'd.py', 'data']
_contents_test('pyi_pkgres_testpkg.subpkg1', expected)

# Subpackage #2
if not is_frozen:
    # Cannot list non-existing directory.
    expected = ['__init__.py', 'mod.py', 'subsubpkg21']
    _contents_test('pyi_pkgres_testpkg.subpkg2', expected)

# Sub-subpackage in subpackage #2
if not is_frozen:
    # Cannot list non-existing directory.
    expected = ['__init__.py', 'mod.py']
    _contents_test('pyi_pkgres_testpkg.subpkg2.subsubpkg21', expected)

# Subpackage #3
expected = ['__init__.py', '_datafile.json']
_contents_test('pyi_pkgres_testpkg.subpkg3', expected)

########################################################################
#              Validate importlib.resources.is_resource()              #
########################################################################
# In general, files (source or data) count as resources, directories do not.

# Querying non-existant resource: return False instead of raising FileNotFoundError
assert not importlib_resources_is_resource('pyi_pkgres_testpkg', 'subpkg_nonexistant')
assert not importlib_resources_is_resource('pyi_pkgres_testpkg.subpkg1', 'nonexistant.txt')

# NOTE: frozen reader does not list .py files (nor equivalent .pyc ones)
assert importlib_resources_is_resource('pyi_pkgres_testpkg', '__init__.py') is not is_frozen
assert importlib_resources_is_resource('pyi_pkgres_testpkg', '__init__.py') is not is_frozen
assert importlib_resources_is_resource('pyi_pkgres_testpkg', 'a.py') is not is_frozen
assert importlib_resources_is_resource('pyi_pkgres_testpkg', 'b.py') is not is_frozen

assert not importlib_resources_is_resource('pyi_pkgres_testpkg', 'subpkg1')
assert not importlib_resources_is_resource('pyi_pkgres_testpkg', 'subpkg2')  # Non-existent in frozen variant.
assert not importlib_resources_is_resource('pyi_pkgres_testpkg', 'subpkg3')

assert importlib_resources_is_resource('pyi_pkgres_testpkg.subpkg1', '__init__.py') is not is_frozen
assert not importlib_resources_is_resource('pyi_pkgres_testpkg.subpkg1', 'data')

# Try to specify a sub-path; should raise ValueError.
try:
    ret = importlib_resources_is_resource('pyi_pkgres_testpkg.subpkg1', 'data/entry1.txt')
except ValueError:
    pass
except Exception:
    raise
else:
    assert False, "Expected a ValueError!"

if not is_frozen:
    assert importlib_resources_is_resource('pyi_pkgres_testpkg.subpkg2', 'mod.py')

assert importlib_resources_is_resource('pyi_pkgres_testpkg.subpkg3', '_datafile.json')


########################################################################
#                  Validate importlib.resources.path()                 #
########################################################################
# The path() function returns on-disk path. If the resource was originally on disk, direct path to it is returned.
# Otherwise, path to a temporary file is returned. This function is probably superseded by files() and as_file(), which
# are more flexible; for example, path() does not allow access to files in sub-directories (only files that are directly
# within a package directory).
def _path_test(pkgname, resource, expected_data):
    with importlib_resources_path(pkgname, resource) as pth:
        assert isinstance(pth, pathlib.Path)
        with open(pth, 'rb') as fp:
            data = fp.read()
        if expected_data is not None:
            assert data.splitlines() == expected_data.splitlines()  # Split to avoid OS-specific newline discrepancies.


if not is_frozen:
    expected_data = b"""from . import a, b  # noqa: F401\nfrom . import subpkg1, subpkg2, subpkg3  # noqa: F401\n"""
    _path_test('pyi_pkgres_testpkg', '__init__.py', expected_data)

if not is_frozen:
    expected_data = b"""#\n"""
    _path_test('pyi_pkgres_testpkg.subpkg2', 'mod.py', expected_data)

expected_data = b"""{\n  "_comment": "Data file in supbkg3."\n}\n"""
_path_test('pyi_pkgres_testpkg.subpkg3', '_datafile.json', expected_data)

# Try with a non-existant file; should raise FileNotFoundError.
# NOTE: importlib.resources in python 3.9 seems to do so, but importlib_resources 5.2.2 does not...
try:
    _path_test('pyi_pkgres_testpkg.subpkg1', 'nonexistant.txt', None)
except FileNotFoundError:
    pass
except Exception:
    raise
else:
    assert not is_builtin, "Expected a FileNotFoundError!"

# Try to specify a sub-path; should raise ValueError.
try:
    _path_test('pyi_pkgres_testpkg.subpkg1', 'data/entry1.txt', None)
except ValueError:
    pass
except Exception:
    raise
else:
    assert False, "Expected a ValueError!"

########################################################################
#               Validate importlib.resources.read_binary()             #
########################################################################
# Data file in pyi_pkgres_testpkg.subpkg3
expected_data = b"""{\n  "_comment": "Data file in supbkg3."\n}\n"""
data = importlib_resources_read_binary('pyi_pkgres_testpkg.subpkg3', '_datafile.json')
assert data.splitlines() == expected_data.splitlines()

# Source file in pyi_pkgres_testpkg
if not is_frozen:
    expected_data = b"""from . import a, b  # noqa: F401\nfrom . import subpkg1, subpkg2, subpkg3  # noqa: F401\n"""
    data = importlib_resources_read_binary('pyi_pkgres_testpkg', '__init__.py')
    assert data.splitlines() == expected_data.splitlines()

# Try with non-existant file; should raise FileNotFoundError
try:
    importlib_resources_read_binary('pyi_pkgres_testpkg.subpkg1', 'nonexistant.txt')
except FileNotFoundError:
    pass
except Exception:
    raise
else:
    assert False, "Expected a FileNotFoundError!"

# Try to specify sub-path; should raise ValueError
try:
    importlib_resources_read_binary('pyi_pkgres_testpkg.subpkg1', 'data/entry1.txt')
except ValueError:
    pass
except Exception:
    raise
else:
    assert False, "Expected a ValueError!"

########################################################################
#                Validate importlib.resources.read_text()              #
########################################################################
# Data file in pyi_pkgres_testpkg.subpkg3
expected_data = """{\n  "_comment": "Data file in supbkg3."\n}\n"""
data = importlib_resources_read_text('pyi_pkgres_testpkg.subpkg3', '_datafile.json', encoding='utf8')
assert data.splitlines() == expected_data.splitlines()

# Source file in pyi_pkgres_testpkg
if not is_frozen:
    expected_data = """from . import a, b  # noqa: F401\nfrom . import subpkg1, subpkg2, subpkg3  # noqa: F401\n"""
    data = importlib_resources_read_text('pyi_pkgres_testpkg', '__init__.py', encoding='utf8')
    assert data.splitlines() == expected_data.splitlines()

# Try with non-existant file; should raise FileNotFoundError
try:
    importlib_resources_read_text('pyi_pkgres_testpkg.subpkg1', 'nonexistant.txt', encoding='utf8')
except FileNotFoundError:
    pass
except Exception:
    raise
else:
    assert False, "Expected a FileNotFoundError!"

# Try to specify sub-path; should raise ValueError
try:
    importlib_resources_read_text('pyi_pkgres_testpkg.subpkg1', 'data/entry1.txt', encoding='utf8')
except ValueError:
    pass
except Exception:
    raise
else:
    assert False, "Expected a ValueError!"

########################################################################
#          Validate importlib.resources.files() and as_file()          #
########################################################################
# files() should return a Traversable (or just a plain pathlib.Path). For on-disk resources, as_file() should not be
# opening a temporary-file copy.
pkg_path = importlib_resources_files('pyi_pkgres_testpkg')
subpkg1_path = importlib_resources_files('pyi_pkgres_testpkg.subpkg1')

# assert subpkg1_path == pkg_path / 'subpkg1'  # True only for on-disk resources!

# Try to get data file in a sub-directory with subpath consisting of single string. This simulates the use in
# https://github.com/Unidata/MetPy/blob/a3424de66a44bf3a92b0dcacf4dff82ad7b86712/src/metpy/plots/wx_symbols.py#L24-L25
# that seems to trip up the back-ported importlib_resources when we do not provide our own resource reader. In that
# case, its compatibility adapter ends up triggering the copy-to-temporary-file codepath, which errors out because the
# it ends up generating a temporary file name with separator (that would require creation of intermediate directory).
# It works correctly with built-in importlib.resources in python 3.9 (even if we do not implement a resource reader).
data_path = subpkg1_path / 'data/entry1.txt'
expected_data = b"""Data entry #1 in subpkg1/data.\n"""

with importlib_resources_as_file(data_path) as file_path:
    with open(file_path, 'rb') as fp:
        data = fp.read()
assert data.splitlines() == expected_data.splitlines()

# Try to get a data file in a sub-directory via two paths. The read contents should be the same.
# If we do not provide our own resource reader, neither way of accessing works in frozen version with back-ported
# importlib_resources (˙˙FileNotFoundError: Can't open orphan path˙˙).
# It works correctly with built-in importlib.resources in python 3.9 (even if we do not implement a resource reader).
expected_data = b"""Data entry #2 in `subpkg1/data`.\n"""

data_path = pkg_path / 'subpkg1' / 'data' / 'entry2.md'
with importlib_resources_as_file(data_path) as file_path:
    with open(file_path, 'rb') as fp:
        data = fp.read()
assert data.splitlines() == expected_data.splitlines()

data_path = subpkg1_path / 'data' / 'entry2.md'
with importlib_resources_as_file(data_path) as file_path:
    with open(file_path, 'rb') as fp:
        data = fp.read()
assert data.splitlines() == expected_data.splitlines()
