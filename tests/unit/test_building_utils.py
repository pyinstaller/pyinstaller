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

import os
import sys
import pathlib

import pytest

from PyInstaller.building import utils
from PyInstaller.compat import is_termux


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


def test_should_include_system_binary():
    python_dir = f'python{sys.version_info.major}.{sys.version_info.minor}'
    python_lib = f'libpython{sys.version_info.major}.{sys.version_info.minor}.so'
    if is_termux:
        # NOTE: in Termux environment, /usr is symbolic link to /data/data/com.termux/files/usr
        termux_usr = '/data/data/com.termux/files/usr'
        CASES = (
            # Python shared library; should be always included
            (python_lib, f'{termux_usr}/lib/{python_lib}', [], True),
            (python_lib, f'/usr/lib/{python_lib}', [], True),
            # Python stdlib extension from lib-dynload directory; should be always included
            (f'{python_dir}/lib-dynload/any.so', f'{termux_usr}/lib/{python_dir}/lib-dynload/any.so', [], True),
            (f'{python_dir}/lib-dynload/any.so', f'/usr/lib/{python_dir}/lib-dynload/any.so', [], True),
            # Shared library bundled with a package inside system's site-packages directory; should be always included.
            ('mypackage/any.so', f'{termux_usr}/lib/{python_dir}/site-packages/mypackage/any.so', [], True),
            ('mypackage/any.so', f'/usr/lib/{python_dir}/site-packages/mypackage/any.so', [], True),
            # Some other (system) directory
            ('libany.so', '/etc/libany.so', [], True),
            ('libany.so', f'{termux_usr}/etc/libany.so', [], True),
            ('libany.so', '/usr/etc/libany.so', [], True),
            # Shared library in /data/data/com.termux/files/usr/lib (or /usr/lib), with various exception combinations.
            ('libany.so', f'{termux_usr}/lib/libany.so', ['*any*'], True),
            ('libany.so', '/usr/lib/libany.so', ['*any*'], True),
            ('libany2.so', f'{termux_usr}/lib/libany2.so', ['libnone*', 'libany*'], True),
            ('libany2.so', '/usr/lib/libany2.so', ['libnone*', 'libany*'], True),
            ('libnomatch.so', f'{termux_usr}/lib/libnomatch.so', ['libnone*', 'libany*'], False),
            ('libnomatch.so', '/usr/lib/libnomatch.so', ['libnone*', 'libany*'], False),
            # Shared library in /system/lib; without and with exclusion exception
            ('libc++.so', '/system/lib/libc++.so', [], False),
            ('libc++.so', '/system/lib/libc++.so', ['libc*'], True),
        )
    else:
        # NOTE: nowadays, /lib64 and /lib are symbolic links to their counterparts in /usr. For the sake of
        # completeness, we explicitly test all four possibilities.
        CASES = (
            # Python shared library; should be always included
            (python_lib, f'/lib64/{python_lib}', [], True),
            (python_lib, f'/usr/lib64/{python_lib}', [], True),
            (python_lib, f'/lib/{python_lib}', [], True),
            (python_lib, f'/usr/lib/{python_lib}', [], True),
            # Python stdlib extension from lib-dynload directory; should be always included
            (f'{python_dir}/lib-dynload/any.so', f'/lib64/{python_dir}/lib-dynload/any.so', [], True),
            (f'{python_dir}/lib-dynload/any.so', f'/usr/lib64/{python_dir}/lib-dynload/any.so', [], True),
            (f'{python_dir}/lib-dynload/any.so', f'/lib/{python_dir}/lib-dynload/any.so', [], True),
            (f'{python_dir}/lib-dynload/any.so', f'/usr/lib/{python_dir}/lib-dynload/any.so', [], True),
            # Shared library bundled with a package inside system's site-packages directory; should be always included.
            ('mypackage/any.so', f'/lib64/{python_dir}/site-packages/mypackage/any.so', [], True),
            ('mypackage/any.so', f'/usr/lib64/{python_dir}/site-packages/mypackage/any.so', [], True),
            ('mypackage/any.so', f'/lib/{python_dir}/site-packages/mypackage/any.so', [], True),
            ('mypackage/any.so', f'/usr/lib/{python_dir}/site-packages/mypackage/any.so', [], True),
            # Some other (system) directory
            ('libany.so', '/etc/libany.so', [], True),
            # Shared library in system library directory, with various exception combinations.
            ('libany.so', '/lib64/libany.so', ['*any*'], True),
            ('libany.so', '/usr/lib64/libany.so', ['*any*'], True),
            ('libany.so', '/lib/libany.so', ['*any*'], True),
            ('libany.so', '/usr/lib/libany.so', ['*any*'], True),
            ('libany2.so', '/lib64/libany2.so', ['libnone*', 'libany*'], True),
            ('libany2.so', '/usr/lib64/libany2.so', ['libnone*', 'libany*'], True),
            ('libany2.so', '/lib/libany2.so', ['libnone*', 'libany*'], True),
            ('libany2.so', '/lib64/libany2.so', ['libnone*', 'libany*'], True),
            ('libnomatch.so', '/lib64/libnomatch.so', ['libnone*', 'libany*'], False),
            ('libnomatch.so', '/usr/lib64/libnomatch.so', ['libnone*', 'libany*'], False),
            ('libnomatch.so', '/lib/libnomatch.so', ['libnone*', 'libany*'], False),
            ('libnomatch.so', '/usr/lib/libnomatch.so', ['libnone*', 'libany*'], False),
        )

    for dest_path, src_path, exceptions, expected_result in CASES:
        toc_entry = (dest_path, src_path, 'BINARY')
        assert utils._should_include_system_binary(toc_entry, exceptions) == expected_result
