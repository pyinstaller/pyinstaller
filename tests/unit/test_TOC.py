#-----------------------------------------------------------------------------
# Copyright (c) 2005-2022, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

# This contains tests for the class:``TOC``, see
# https://pyinstaller.readthedocs.io/en/latest/advanced-topics.html#the-toc-and-tree-classes

import os

from PyInstaller.building.datastruct import TOC

ELEMS1 = (
    ('encodings', '/usr/lib/python2.7/encodings/__init__.py', 'PYMODULE'),
    ('_random', '/usr/lib/python2.7/lib-dynload/_random.so', 'EXTENSION'),
    ('libreadline.so.6', '/lib64/libreadline.so.6', 'BINARY'),
)

ELEMS2 = (
    ('li-la-lu', '/home/myself/li-la-su', 'SOMETHING'),
    ('schubidu', '/home/otherguy/schibidu', 'PKG'),
)

ELEMS3 = (('PIL.Image.py', '/usr/lib/python2.7/encodings/__init__.py', 'PYMODULE'),)


def test_init_empty():
    toc = TOC()
    assert len(toc) == 0


def test_init():
    toc = TOC(ELEMS1)
    assert len(toc) == 3
    assert toc == list(ELEMS1)


def test_append():
    toc = TOC(ELEMS1)
    toc.append(('li-la-lu', '/home/myself/li-la-su', 'SOMETHING'))
    expected = list(ELEMS1)
    expected.append(('li-la-lu', '/home/myself/li-la-su', 'SOMETHING'))
    assert toc == expected


def test_append_existing():
    toc = TOC(ELEMS1)
    toc.append(ELEMS1[-1])
    expected = list(ELEMS1)
    assert toc == expected


def test_append_keep_filename():
    # The entry name in TOC should be identical to the one added (i.e., the case must be preserved).
    toc = TOC()
    entry = ('EnCodIngs', '/usr/lib/python2.7/encodings.py', 'BINARY')
    toc.append(entry)
    assert toc[0][0] == entry[0]


def test_insert():
    toc = TOC(ELEMS1)
    toc.insert(1, ('li-la-lu', '/home/myself/li-la-su', 'SOMETHING'))
    expected = list(ELEMS1)
    expected.insert(1, ('li-la-lu', '/home/myself/li-la-su', 'SOMETHING'))
    assert toc == expected


def test_insert_existing():
    toc = TOC(ELEMS1)
    toc.insert(0, ELEMS1[-1])
    toc.insert(1, ELEMS1[-1])
    expected = list(ELEMS1)
    assert toc == expected


def test_insert_keep_filename():
    # The entry name in TOC should be identical to the one added (i.e., the case must be preserved).
    toc = TOC()
    entry = ('EnCodIngs', '/usr/lib/python2.7/encodings.py', 'BINARY')
    toc.insert(1, entry)
    assert toc[0][0] == entry[0]


def test_extend():
    toc = TOC(ELEMS1)
    toc.extend(ELEMS2)
    expected = list(ELEMS1)
    expected.extend(ELEMS2)
    assert toc == expected


def test_extend_existing():
    toc = TOC(ELEMS1)
    toc.extend(ELEMS1)
    expected = list(ELEMS1)
    assert toc == expected


def test_add_list():
    toc = TOC(ELEMS1)
    other = list(ELEMS2)
    result = toc + other
    assert result is not toc
    assert result is not other
    assert isinstance(result, TOC)
    expected = list(ELEMS1) + list(ELEMS2)
    assert result == expected


def test_add_tuple():
    toc = TOC(ELEMS1)
    other = ELEMS2
    result = toc + other
    assert result is not toc
    assert result is not other
    assert isinstance(result, TOC)
    expected = list(ELEMS1) + list(ELEMS2)
    assert result == expected


def test_add_toc():
    toc = TOC(ELEMS1)
    other = TOC(ELEMS2)
    result = toc + other
    assert result is not toc
    assert result is not other
    assert isinstance(result, TOC)
    expected = list(ELEMS1) + list(ELEMS2)
    assert result == expected


def test_radd_list():
    toc = TOC(ELEMS1)
    other = list(ELEMS2)
    result = other + toc
    assert result is not toc
    assert result is not other
    assert isinstance(result, TOC)
    expected = list(ELEMS2) + list(ELEMS1)
    assert result == expected


def test_radd_tuple():
    toc = TOC(ELEMS1)
    other = ELEMS2
    result = other + toc
    assert result is not toc
    assert result is not other
    assert isinstance(result, TOC)
    expected = list(ELEMS2) + list(ELEMS1)
    assert result == expected


def test_radd_toc():
    toc = TOC(ELEMS1)
    other = TOC(ELEMS2)
    result = other + toc
    assert result is not toc
    assert result is not other
    assert isinstance(result, TOC)
    expected = list(ELEMS2) + list(ELEMS1)
    assert result == expected


def test_sub_list():
    toc = TOC(ELEMS1) + ELEMS2
    other = list(ELEMS2)
    result = toc - other
    assert result is not toc
    assert result is not other
    assert isinstance(result, TOC)
    expected = list(ELEMS1)
    assert result == expected


def test_sub_tuple():
    toc = TOC(ELEMS1) + ELEMS2
    other = ELEMS2
    result = toc - other
    assert result is not toc
    assert result is not other
    assert isinstance(result, TOC)
    expected = list(ELEMS1)
    assert result == expected


def test_sub_toc():
    toc = TOC(ELEMS1) + ELEMS2
    other = TOC(ELEMS2)
    result = toc - other
    assert result is not toc
    assert result is not other
    assert isinstance(result, TOC)
    expected = list(ELEMS1)
    assert result == expected


def test_sub_non_existing():
    toc = TOC(ELEMS1)
    other = ELEMS3
    result = toc - other
    assert result is not toc
    assert result is not other
    assert isinstance(result, TOC)
    expected = list(ELEMS1)
    assert result == expected


def test_rsub_list():
    toc = TOC(ELEMS1)
    other = list(ELEMS1) + list(ELEMS2)
    result = other - toc
    assert result is not toc
    assert result is not other
    assert isinstance(result, TOC)
    expected = list(ELEMS2)
    assert result == expected


def test_rsub_tuple():
    toc = TOC(ELEMS1)
    other = tuple(list(ELEMS1) + list(ELEMS2))
    result = other - toc
    assert result is not toc
    assert result is not other
    assert isinstance(result, TOC)
    expected = list(ELEMS2)
    assert result == expected


def test_rsub_toc():
    toc = TOC(ELEMS1)
    other = TOC(ELEMS1) + ELEMS2
    result = other - toc
    assert result is not toc
    assert result is not other
    assert isinstance(result, TOC)
    expected = list(ELEMS2)
    assert result == expected


def test_rsub_non_existing():
    toc = TOC(ELEMS3)
    other = ELEMS1
    result = other - toc
    assert result is not toc
    assert result is not other
    assert isinstance(result, TOC)
    expected = list(ELEMS1)
    assert result == expected


def test_sub_after_setitem():
    toc = TOC(ELEMS1)
    toc[1] = ('lib-dynload/_random', '/usr/lib/python2.7/lib-dynload/_random.so', 'EXTENSION')
    toc -= []
    assert len(toc) == 3


def test_sub_after_sub():
    toc = TOC(ELEMS1)
    toc -= [ELEMS1[0]]
    toc -= [ELEMS1[1]]
    expected = list(ELEMS1[2:])
    assert toc == expected


def test_setitem_1():
    toc = TOC()
    toc[:] = ELEMS1
    for e in ELEMS1:
        assert e in toc
        assert e[0] in toc.filenames


def test_setitem_2():
    toc = TOC(ELEMS1)
    toc[1] = ELEMS3[0]

    assert ELEMS1[0] in toc
    assert ELEMS1[0][0] in toc.filenames

    assert ELEMS3[0] in toc
    assert ELEMS3[0][0] in toc.filenames

    assert ELEMS1[2] in toc
    assert ELEMS1[2][0] in toc.filenames

    for e in toc:
        assert e[0] in toc.filenames


# The following tests verify that case-insensitive comparisons are used on Windows and only for
# appropriate TOC entry types
is_case_sensitive = os.path.normcase('CamelCase') == 'CamelCase'


def test_append_other_case_mixed():
    # Try appending a BINARY entry with same-but-differently-cased name as an existing PYMODULE entry.
    # Not added on Windows, added elsewhere.
    toc = TOC(ELEMS1)
    elem = ('EnCodIngs', '/usr/lib/python2.7/encodings.py', 'BINARY')
    toc.append(elem)
    expected = list(ELEMS1)
    if is_case_sensitive:
        expected.append(elem)
    assert toc == expected


def test_append_other_case_pymodule():
    # Try appending a PYMODULE entry with same-but-differently-cased name as an existing PYMODULE entry.
    # Added on all OSes.
    toc = TOC(ELEMS1)
    elem = ('EnCodIngs', '/usr/lib/python2.7/encodings.py', 'PYMODULE')
    toc.append(elem)
    expected = list(ELEMS1)
    expected.append(elem)
    assert toc == expected


def test_append_other_case_binary():
    # Try appending a BINARY entry with same-but-differently-cased name as an existing BINARY entry.
    # Not added on Windows, added elsewhere.
    toc = TOC(ELEMS1)
    elem = ('LiBrEADlInE.so.6', '/lib64/libreadline.so.6', 'BINARY')
    toc.append(elem)
    expected = list(ELEMS1)
    if is_case_sensitive:
        expected.append(elem)
    assert toc == expected


def test_insert_other_case_mixed():
    # Try inserting a BINARY entry with same-but-differently-cased name as an existing PYMODULE entry.
    # Not added on Windows, added elsewhere.
    toc = TOC(ELEMS1)
    elem = ('EnCodIngs', '/usr/lib/python2.7/encodings.py', 'BINARY')
    toc.insert(1, elem)
    expected = list(ELEMS1)
    if is_case_sensitive:
        expected.insert(1, elem)
    assert toc == expected


def test_insert_other_case_pymodule():
    # Try appending a PYMODULE entry with same-but-differently-cased name as an existing PYMODULE entry.
    # Added on all OSes.
    toc = TOC(ELEMS1)
    elem = ('EnCodIngs', '/usr/lib/python2.7/encodings.py', 'PYMODULE')
    toc.insert(1, elem)
    expected = list(ELEMS1)
    expected.insert(1, elem)
    assert toc == expected


def test_insert_other_case_binary():
    # Try appending a BINARY entry with same-but-differently-cased name as an existing BINARY entry.
    # Not added on Windows, added elsewhere.
    toc = TOC(ELEMS1)
    elem = ('LiBrEADlInE.so.6', '/lib64/libreadline.so.6', 'BINARY')
    toc.insert(1, elem)
    expected = list(ELEMS1)
    if is_case_sensitive:
        expected.insert(1, elem)
    assert toc == expected


# Test that subtraction works as expected when the entry specifies only the name, without path and typecode.
# On Windows, the subtraction should work with case-normalized names for BINARY and DATA entries, while on other
# OSes, it should be case sensitive for all entry types.
def test_subtract_same_case_binary():
    # Subtract with same case - removes element on all OSes
    toc = TOC(ELEMS1)
    elem = ('libCamelCase.so.1', '/lib64/libcamelcase.so.1', 'BINARY')
    toc.append(elem)
    toc -= [('libCamelCase.so.1', None, None)]
    expected = list(ELEMS1)
    assert toc == expected


def test_subtract_other_case_binary():
    # Subtract with different case - removes element only on Windows
    toc = TOC(ELEMS1)
    elem = ('libCamelCase.so.1', '/lib64/libcamelcase.so.1', 'BINARY')
    toc.append(elem)
    toc -= [('libcamelcase.so.1', None, None)]
    expected = list(ELEMS1)
    if is_case_sensitive:
        expected.append(elem)
    assert toc == expected


def test_subtract_same_case_pymodule():
    # Subtract with same case - removes element on all OSes
    toc = TOC(ELEMS1)
    elem = ('modCamelCase', '/lib64/python3.9/site-packages/modCamelCase.py', 'PYMODULE')
    toc.append(elem)
    toc -= [('modCamelCase', None, None)]
    expected = list(ELEMS1)
    assert toc == expected


def test_subtract_other_case_pymodule():
    # Subtract with different case - removes element only on Windows
    toc = TOC(ELEMS1)
    elem = ('modCamelCase', '/lib64/python3.9/site-packages/modCamelCase.py', 'PYMODULE')
    toc.append(elem)
    toc -= [('modcamelcase', None, None)]
    expected = list(ELEMS1)
    expected.append(elem)
    assert toc == expected
