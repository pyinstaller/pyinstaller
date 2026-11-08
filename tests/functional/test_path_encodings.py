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

import subprocess

import pytest

from PyInstaller.utils.tests import importorskip


def test_ascii_path(pyi_builder):
    dist_dir = str(pyi_builder._dist_dir)

    dist_dir_ascii = dist_dir.encode('ascii', 'replace').decode('ascii')
    if dist_dir != dist_dir_ascii:
        pytest.skip(reason="Default build path not ASCII, skipping...")

    pyi_builder.test_script('pyi_path_encoding.py')


_UNICODE_FILENAME = 'ěščřžýáíé日本語'


def _codepage_filename():
    # Create some bytes and decode with the current codepage to get a filename that is guaranteed to encode with the
    # current codepage. Assumes a one-byte codepage, i.e., not cp937 (shift-JIS) which is multibyte.
    return bytes(bytearray(range(0x80, 0x86))).decode('mbcs')


# Build into a subdirectory named after a non-ASCII filename, and use a (non-ASCII) temporary directory, to verify
# that paths with the given encodings are handled correctly throughout the build and at run-time. Each parameter set
# is (subdir_kind, extra_env), where `subdir_kind` selects the non-ASCII filename and `extra_env` are additional
# environment variables set for the test.
@pytest.mark.parametrize(
    "subdir_kind, extra_env",
    [
        # If we set the locale to 'C', mbstowcs should be completely useless. This test verifies that _Py_char2wchar
        # will decode the "undecodable" bytes and will decode even filenames that weren't encoded with the locale
        # encoding.
        pytest.param('unicode', {'LC_ALL': 'C'}, marks=pytest.mark.linux, id='linux-non-unicode-path'),
        # Mac and Linux should handle 'unicode' type filenames without problem.
        pytest.param('unicode', {}, marks=[pytest.mark.darwin, pytest.mark.linux], id='osx-linux-unicode-path'),
        pytest.param('codepage', {}, marks=pytest.mark.win32, id='win-codepage-path'),
        # Both eastern European and Japanese characters - no codepage should encode this; codepage encoding would
        # replace some of these chars with "???". To test what happens with a non-ANSI tempdir, we will also need to
        # pass the TMP environ as wide chars.
        pytest.param('unicode', {}, marks=pytest.mark.win32, id='win-non-codepage-path'),
    ],
)
def test_path_encoding_non_ascii_dist_dir(pyi_builder, monkeypatch, subdir_kind, extra_env):
    subdir_name = _codepage_filename() if subdir_kind == 'codepage' else _UNICODE_FILENAME

    for key, value in extra_env.items():
        monkeypatch.setenv(key, value)

    pyi_builder._dist_dir = pyi_builder._dist_dir / subdir_name

    tmp = pyi_builder._tmp_path / f"{subdir_name}_TMP"
    tmp.mkdir()

    monkeypatch.setenv('TMPDIR', str(tmp))
    monkeypatch.setenv('TMP', str(tmp))

    pyi_builder.test_script('pyi_path_encoding.py')


@pytest.mark.win32
def test_win_codepage_path_disabled_shortfilename(pyi_builder, monkeypatch):
    cp_filename = _codepage_filename()

    pyi_builder._dist_dir = pyi_builder._dist_dir / cp_filename

    # Try to remove ShortFileName from this folder using `fsutil`. Requires admin privileges, so `xfail` if we do not
    # have them. `8dot3name strip` only affects subfolders, so pass the folder containing our codepage filename.
    pyi_builder._dist_dir.mkdir(parents=True)  # Ensure directory exists so we can modify it with `fsutil`.
    if subprocess.call(['fsutil', '8dot3name', 'strip', str(pyi_builder._dist_dir)]):
        pytest.xfail("Administrator privileges required to strip ShortFileName.")

    tmp = pyi_builder._tmp_path / f"{cp_filename}_TMP"
    tmp.mkdir()

    monkeypatch.setenv('TMPDIR', str(tmp))
    monkeypatch.setenv('TMP', str(tmp))

    pyi_builder.test_script('pyi_path_encoding.py')


@pytest.mark.win32
@importorskip('win32api')
def test_win_py3_no_shortpathname(pyi_builder):
    pyi_builder.test_script('pyi_win_py3_no_shortpathname.py')


@pytest.mark.win32
@importorskip('win32api')
def test_win_TEMP_has_shortpathname(pyi_builder, monkeypatch, tmp_path):
    """
    Test if script if pass if $TMP holds a short path name.
    """
    tmp = tmp_path / "longlongfilename" / "xxx"
    tmp.mkdir(parents=True, exist_ok=True)
    import win32api
    tmp = win32api.GetShortPathName(str(tmp))
    monkeypatch.setenv("TMP", tmp)
    monkeypatch.setenv("TEMP", tmp)
    pyi_builder.test_script('pyi_win_py3_no_shortpathname.py')
