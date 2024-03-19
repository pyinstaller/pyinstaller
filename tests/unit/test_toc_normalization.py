#-----------------------------------------------------------------------------
# Copyright (c) 2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

# Tests for explicit TOC list normalization that replaced the implicit normalization with class:``TOC``.
import copy
import pathlib

from PyInstaller import compat
from PyInstaller.building.datastruct import normalize_pyz_toc, normalize_toc

# Tests for regular TOC normalization.

_BASE_TOC = [
    ('libpython3.10.so', '/usr/lib64/libpython3.10.so', 'BINARY'),
    ('libsomething.so', '/usr/local/lib64/libsomething.so', 'BINARY'),
    ('README', '/home/user/tmp/README', 'DATA'),
    (str(pathlib.PurePath('data/data.csv')), '/home/user/tmp/data/data.csv', 'DATA'),
    ('dependency.bin', 'other_multipackage:dependency.bin', 'DEPENDENCY'),
    ('myextension.so', 'myextension.so', 'EXTENSION'),
]


def test_normalize_toc_no_duplicates():
    # No duplicates. We expect the output list to match the input list.
    toc = copy.copy(_BASE_TOC)
    expected_toc = _BASE_TOC

    normalized_toc = normalize_toc(toc)
    assert normalized_toc == expected_toc


def test_normalize_toc_duplicate_binary():
    # A duplicated BINARY entry. We expect the (second) duplicate to be removed.
    toc = copy.copy(_BASE_TOC)
    toc.insert(2, ('libsomething.so', '/opt/something/lib/libsomething.so', 'BINARY'))
    expected_toc = _BASE_TOC

    normalized_toc = normalize_toc(toc)
    assert normalized_toc == expected_toc


def test_normalize_toc_duplicate_binary_case_sensitive():
    # A BINARY entry that is a duplicate only on case-insensitive OSes.
    toc = copy.copy(_BASE_TOC)
    toc.insert(2, ('libSoMeThInG.so', '/opt/something/lib/libSoMeThInG.so', 'BINARY'))
    expected_toc = _BASE_TOC

    if compat.is_win:
        expected_toc = _BASE_TOC
    else:
        expected_toc = toc

    normalized_toc = normalize_toc(toc)
    assert normalized_toc == expected_toc


def test_normalize_toc_duplicate_data():
    # A duplicated DATA entry. We expect the (second) duplicate to be removed.
    toc = copy.copy(_BASE_TOC)
    toc.insert(3, ('README', '/home/user/tmp/README', 'DATA'))
    expected_toc = _BASE_TOC

    normalized_toc = normalize_toc(toc)
    assert normalized_toc == expected_toc


def test_normalize_toc_duplicate_data_case_sensitive():
    # A DATA entry that is a duplicate on case-insensitive OSes.
    toc = copy.copy(_BASE_TOC)
    toc.insert(-1, ('readme', '/home/user/tmp-other/readme', 'DATA'))
    expected_toc = _BASE_TOC

    if compat.is_win:
        expected_toc = _BASE_TOC
    else:
        expected_toc = toc

    normalized_toc = normalize_toc(toc)
    assert normalized_toc == expected_toc


def test_normalize_toc_conflicting_binary_and_data1():
    # An entry that's duplicated as both BINARY and DATA.
    # BINARY entry should be kept.
    toc = copy.copy(_BASE_TOC)
    toc.insert(2, ('libsomething.so', '/usr/local/lib64/libsomething.so', 'DATA'))  # Insert after BINARY entry
    expected_toc = _BASE_TOC

    normalized_toc = normalize_toc(toc)
    assert normalized_toc == expected_toc


def test_normalize_toc_conflicting_binary_and_data2():
    # An entry that's duplicated as both BINARY and DATA, in reverse order.
    # BINARY entry should be kept.
    toc = copy.copy(_BASE_TOC)
    toc.insert(1, ('libsomething.so', '/usr/local/lib64/libsomething.so', 'DATA'))  # Insert before BINARY entry
    expected_toc = _BASE_TOC

    normalized_toc = normalize_toc(toc)
    assert normalized_toc == expected_toc


def test_normalize_toc_multipackage_dependency():
    # An entry that's duplicated as both BINARY, DATA, EXTENSION, and DEPENDENCY.
    # DEPENDENCY should have the highest priority of the four.
    # The priority-based replacement during normalization might not preserve the order, so we need to sort the
    # resulting and expected TOC before comparing them. In this particular case, we insert duplicates at the
    # start of the list, so de-duplication effectively moves the DEPENDENCY entry to the first place in the
    # output list.
    toc = copy.copy(_BASE_TOC)
    toc.insert(0, ('dependency.bin', '/mnt/somewhere/dependency.bin', 'EXTENSION'))
    toc.insert(0, ('dependency.bin', '/mnt/somewhere/dependency.bin', 'BINARY'))
    toc.insert(0, ('dependency.bin', '/mnt/somewhere/dependency.bin', 'DATA'))
    expected_toc = _BASE_TOC

    normalized_toc = normalize_toc(toc)
    assert sorted(normalized_toc) == sorted(expected_toc)


def test_normalize_toc_with_parent_pardir_loops():
    # Check that de-duplication works even if destination paths contain local loop with parent directory (..) components
    # but can be normalized to the same path. Furthermore, we expect TOC normalization to sanitize the dest_name with
    # normalized version.
    toc = [
        (
            str(pathlib.PurePath('numpy/core/../../numpy.libs/libquadmath-2d0c479f.so.0.0.0')),
            '/path/to/venv/lib/python3.11/site-packages/numpy/core/../../numpy.libs/libquadmath-2d0c479f.so.0.0.0',
            'BINARY',
        ),
        (
            str(pathlib.PurePath('numpy/linalg/../../numpy.libs/libquadmath-2d0c479f.so.0.0.0')),
            '/path/to/venv/lib/python3.11/site-packages/numpy/linalg/../../numpy.libs/libquadmath-2d0c479f.so.0.0.0',
            'BINARY',
        ),
    ]
    expected_toc = [
        (
            str(pathlib.PurePath('numpy.libs/libquadmath-2d0c479f.so.0.0.0')),
            '/path/to/venv/lib/python3.11/site-packages/numpy/core/../../numpy.libs/libquadmath-2d0c479f.so.0.0.0',
            'BINARY',
        ),
    ]

    normalized_toc = normalize_toc(toc)
    assert sorted(normalized_toc) == sorted(expected_toc)


# Tests for PYZ TOC normalization.
_BASE_PYZ_TOC = [
    ('copy', '/usr/lib64/python3.11/copy.py', 'PYMODULE'),
    ('csv', '/usr/lib64/python3.11/csv.py', 'PYMODULE'),
    ('dataclasses', '/usr/lib64/python3.11/dataclasses.py', 'PYMODULE'),
    ('datetime', '/usr/lib64/python3.11/datetime.py', 'PYMODULE'),
    ('decimal', '/usr/lib64/python3.11/decimal.py', 'PYMODULE'),
    ('mymodule1', 'mymodule1.py', 'PYMODULE'),
    ('mymodule2', 'mymodule2.py', 'PYMODULE'),
]


def test_normalize_pyz_toc_no_duplicates():
    # No duplicates. We expect the output list to match the input list.
    toc = copy.copy(_BASE_PYZ_TOC)
    expected_toc = _BASE_PYZ_TOC

    normalized_toc = normalize_pyz_toc(toc)
    assert normalized_toc == expected_toc


def test_normalize_pyz_toc_duplicates():
    # Duplicated entry. We expect the (second) duplicate to be removed.
    toc = copy.copy(_BASE_PYZ_TOC)
    toc.insert(6, ('mymodule1', 'some-other-path/mymodule1.py', 'PYMODULE'))
    expected_toc = _BASE_PYZ_TOC

    normalized_toc = normalize_pyz_toc(toc)
    assert normalized_toc == expected_toc


def test_normalize_pyz_toc_case_sensitivity():
    # Duplicated entry with different case. In PYZ, the entries are case-sensitive, so the list is not modified.
    toc = copy.copy(_BASE_PYZ_TOC)
    toc.insert(6, ('MyMoDuLe1', 'some-other-path/MyMoDuLe1.py', 'PYMODULE'))
    expected_toc = toc

    normalized_toc = normalize_pyz_toc(toc)
    assert normalized_toc == expected_toc
