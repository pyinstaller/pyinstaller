#-----------------------------------------------------------------------------
# Copyright (c) 2005-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import importlib.machinery
import os
import pathlib

import pytest

from PyInstaller.building import utils


def test_format_binaries_and_datas_not_found_raises_error(tmp_path):
    datas = [('non-existing.txt', '.')]
    (tmp_path / 'existing.txt').touch()  # Create a file with different name, for sanity check.
    # TODO Tighten test when introducing PyInstaller.exceptions
    with pytest.raises(SystemExit):
        utils.format_binaries_and_datas(datas, str(tmp_path))


def test_format_binaries_and_datas_empty_src(tmp_path):
    # `format_binaries_and_datas()` must disallow empty src in `binaries`/`datas` tuples, as those result in implicit
    # collection of the whole current working directory .
    datas = [('', '.')]
    with pytest.raises(SystemExit, match="Empty SRC is not allowed"):
        utils.format_binaries_and_datas(datas, str(tmp_path))


def test_format_binaries_and_datas_basic(tmp_path):
    # (src, dest) tuples to be passed to format_binaries_and_datas()
    DATAS = (
        ('existing.txt', '.'),
        ('other.txt', 'foo'),
        ('*.log', 'logs'),
        ('a/*.log', 'lll'),
        ('a/here.tex', '.'),
        ('b/[abc].tex', 'tex'),
    )

    # Expected entries; they are listed as (src, dest) tuples for readability; the subsequent code transforms them into
    # (dest, src) tuples format used by format_binaries_and_datas().
    EXPECTED = (
        ('existing.txt', 'existing.txt'),
        ('other.txt', 'foo/other.txt'),
        ('aaa.log', 'logs/aaa.log'),
        ('bbb.log', 'logs/bbb.log'),
        ('a/xxx.log', 'lll/xxx.log'),
        ('a/yyy.log', 'lll/yyy.log'),
        ('a/here.tex', 'here.tex'),
        ('b/a.tex', 'tex/a.tex'),
        ('b/b.tex', 'tex/b.tex'),
    )

    # Normalize separator in source paths
    datas = [(os.path.normpath(src), dest) for src, dest in DATAS]

    # Convert the (src, dest) entries from EXPECTED into (dest, src) format, and turn `src` into full path.
    expected = set()
    for src, dest in EXPECTED:
        src_path = tmp_path / src
        dest_path = pathlib.PurePath(dest)  # Normalize separators.
        # Create the file
        src_path.parent.mkdir(parents=True, exist_ok=True)
        src_path.touch()
        # Expected entry
        expected.add((str(dest_path), str(src_path)))

    # Create some additional files that should not be included.
    (tmp_path / 'not.txt').touch()
    (tmp_path / 'a' / 'not.txt').touch()
    (tmp_path / 'b' / 'not.txt').touch()

    res = utils.format_binaries_and_datas(datas, str(tmp_path))
    assert res == expected


def test_format_binaries_and_datas_with_bracket(tmp_path):
    # See issue #2314: the filename contains brackets which are interpreted by glob().
    DATAS = (
        (('b/[abc].tex'), 'tex'),
    )  # yapf: disable

    EXPECTED = (
        ('b/[abc].tex', 'tex/[abc].tex'),
    )  # yapf: disable

    # Normalize separator in source paths
    datas = [(os.path.normpath(src), dest) for src, dest in DATAS]

    # Convert the (src, dest) entries from EXPECTED into (dest, src) format, and turn `src` into full path.
    expected = set()
    for src, dest in EXPECTED:
        src_path = tmp_path / src
        dest_path = pathlib.PurePath(dest)  # Normalize separators.
        # Create the file
        src_path.parent.mkdir(parents=True, exist_ok=True)
        src_path.touch()
        # Expected entry
        expected.add((str(dest_path), str(src_path)))

    # Create some additional files that should not be included.
    (tmp_path / 'tex').mkdir(parents=True, exist_ok=True)
    (tmp_path / 'tex' / 'not.txt').touch()

    res = utils.format_binaries_and_datas(datas, str(tmp_path))
    assert res == expected


def test_add_suffix_to_extension():
    SUFFIX = importlib.machinery.EXTENSION_SUFFIXES[0]
    # Each test case is a tuple of four values:
    #  * input dest_name
    #  * output (expected) dest_name
    #  * src
    #  * typecode
    # where (dest_name, src_name, typecode) is a TOC entry tuple.
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
        dest_name1 = str(pathlib.PurePath(case[0]))
        dest_name2 = str(pathlib.PurePath(case[1]))
        src_name = str(pathlib.PurePath(case[2]))
        typecode = case[3]

        toc = (dest_name1, src_name, typecode)
        toc_expected = (dest_name2, src_name, typecode)

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
