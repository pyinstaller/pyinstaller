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

# This contains tests for the class:``TOC``, see
# https://pyinstaller.readthedocs.io/en/latest/advanced-topics.html#the-toc-and-tree-classes

import pytest

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
    # name in TOC should be the same as the one added
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
    # name in TOC should be the same as the one added
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


# The following tests verify that case-insensitive comparisons are used on Windows and only for
# appropriate TOC entry types


@pytest.mark.win32
def test_append_other_case_mixed():
    # If a binary file is added with the same filename as an existing pymodule, it should not be added.
    toc = TOC(ELEMS1)
    elem = ('EnCodIngs', '/usr/lib/python2.7/encodings.py', 'BINARY')
    toc.append(elem)
    expected = list(ELEMS1)
    assert toc == expected


@pytest.mark.win32
def test_append_other_case_pymodule():
    # Python modules should not use C-I comparisons. Both 'encodings' and 'EnCodIngs' should be added.
    toc = TOC(ELEMS1)
    elem = ('EnCodIngs', '/usr/lib/python2.7/encodings.py', 'PYMODULE')
    toc.append(elem)
    expected = list(ELEMS1)
    expected.append(elem)
    assert toc == expected


@pytest.mark.win32
def test_append_other_case_binary():
    # Binary files should use C-I comparisons. 'LiBrEADlInE.so.6' should not be added.
    toc = TOC(ELEMS1)
    toc.append(('LiBrEADlInE.so.6', '/lib64/libreadline.so.6', 'BINARY'))
    expected = list(ELEMS1)
    assert toc == expected


@pytest.mark.win32
def test_insert_other_case_mixed():
    # If a binary file is added with the same filename as an existing pymodule, it should not be added.
    toc = TOC(ELEMS1)
    elem = ('EnCodIngs', '/usr/lib/python2.7/encodings.py', 'BINARY')
    toc.insert(1, elem)
    expected = list(ELEMS1)
    assert toc == expected


@pytest.mark.win32
def test_insert_other_case_pymodule():
    # Python modules should not use C-I comparisons. Both 'encodings' and 'EnCodIngs' should be added.
    toc = TOC(ELEMS1)
    elem = ('EnCodIngs', '/usr/lib/python2.7/encodings.py', 'PYMODULE')
    toc.insert(1, elem)
    expected = list(ELEMS1)
    expected.insert(1, elem)
    assert toc == expected


@pytest.mark.win32
def test_insert_other_case_binary():
    # Binary files should use C-I comparisons. 'LiBrEADlInE.so.6' should not be added.
    toc = TOC(ELEMS1)
    toc.insert(1, ('LiBrEADlInE.so.6', '/lib64/libreadline.so.6', 'BINARY'))
    expected = list(ELEMS1)
    assert toc == expected
