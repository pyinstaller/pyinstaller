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

import pytest
import os
import pathlib
from importlib.machinery import EXTENSION_SUFFIXES

from PyInstaller.building import utils


def test_format_binaries_and_datas_not_found_raises_error(tmpdir):
    datas = [('non-existing.txt', '.')]
    tmpdir.join('existing.txt').ensure()
    # TODO Tighten test when introducing PyInstaller.exceptions
    with pytest.raises(SystemExit):
        utils.format_binaries_and_datas(datas, str(tmpdir))


def test_format_binaries_and_datas_1(tmpdir):
    def _(path):
        return os.path.join(*path.split('/'))

    datas = [
        (_('existing.txt'), '.'),
        (_('other.txt'), 'foo'),
        (_('*.log'), 'logs'),
        (_('a/*.log'), 'lll'),
        (_('a/here.tex'), '.'),
        (_('b/[abc].tex'), 'tex'),
    ]

    expected = set()
    for dest, src in (
        ('existing.txt', 'existing.txt'),
        ('foo/other.txt', 'other.txt'),
        ('logs/aaa.log', 'aaa.log'),
        ('logs/bbb.log', 'bbb.log'),
        ('lll/xxx.log', 'a/xxx.log'),
        ('lll/yyy.log', 'a/yyy.log'),
        ('here.tex', 'a/here.tex'),
        ('tex/a.tex', 'b/a.tex'),
        ('tex/b.tex', 'b/b.tex'),
    ):
        src = tmpdir.join(_(src)).ensure()
        expected.add((_(dest), str(src)))

    # add some files which are not included
    tmpdir.join(_('not.txt')).ensure()
    tmpdir.join(_('a/not.txt')).ensure()
    tmpdir.join(_('b/not.txt')).ensure()

    res = utils.format_binaries_and_datas(datas, str(tmpdir))
    assert res == expected


def test_format_binaries_and_datas_with_bracket(tmpdir):
    # See issue #2314: the filename contains brackets which are interpreted by glob().

    def _(path):
        return os.path.join(*path.split('/'))

    datas = [(_('b/[abc].tex'), 'tex')]

    expected = set()
    for dest, src in (('tex/[abc].tex', 'b/[abc].tex'),):
        src = tmpdir.join(_(src)).ensure()
        expected.add((_(dest), str(src)))

    # add some files which are not included
    tmpdir.join(_('tex/not.txt')).ensure()

    res = utils.format_binaries_and_datas(datas, str(tmpdir))
    assert res == expected


def test_add_suffix_to_extension():
    SUFFIX = EXTENSION_SUFFIXES[0]
    # Each test case is a tuple of four values:
    #  * input inm
    #  * output (expected) inm
    #  * fnm
    #  * typ
    # where (inm, fnm, typ) is a TOC entry tuple.
    # All paths are in POSIX format (and are converted to OS-specific path during the test itself).
    CASES = [
        # Stand-alone extension module
        ('mypkg',
         'mypkg' + SUFFIX,
         'lib38/site-packages/mypkg' + SUFFIX,
         'EXTENSION'),
        # Extension module nested in a package
        ('pkg.subpkg._extension',
         'pkg/subpkg/_extension' + SUFFIX,
         'lib38/site-packages/pkg/subpkg/_extension' + SUFFIX,
         'EXTENSION'),
        # Built-in extension originating from lib-dynload
        ('lib-dynload/_extension',
         'lib-dynload/_extension' + SUFFIX,
         'lib38/lib-dynload/_extension' + SUFFIX,
         'EXTENSION'),
    ]  # yapf: disable

    for case in CASES:
        inm1 = str(pathlib.PurePath(case[0]))
        inm2 = str(pathlib.PurePath(case[1]))
        fnm = str(pathlib.PurePath(case[2]))
        typ = case[3]

        toc = (inm1, fnm, typ)
        toc_expected = (inm2, fnm, typ)

        # Ensure that processing a TOC entry produces expected result.
        toc2 = utils.add_suffix_to_extension(*toc)
        assert toc2 == toc_expected

        # Ensure that processing an already-processed TOC entry leaves it unchanged (i.e., does not mangle it).
        toc3 = utils.add_suffix_to_extension(*toc2)
        assert toc3 == toc2


def test_should_include_system_binary():
    CASES = [
        ('lib-dynload/any', '/usr/lib64/any', [], True),
        ('libany', '/lib64/libpython.so', [], True),
        ('any', '/lib/python/site-packages/any', [], True),
        ('libany', '/etc/libany', [], True),
        ('libany', '/usr/lib/libany', ['*any*'], True),
        ('libany2', '/lib/libany2', ['libnone*', 'libany*'], True),
        ('libnomatch', '/lib/libnomatch', ['libnone*', 'libany*'], False),
    ]

    for case in CASES:
        tuple = (case[0], case[1])
        excepts = case[2]
        expected = case[3]

        assert utils._should_include_system_binary(tuple, excepts) == expected
