# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2005-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import os
import sys
import subprocess

import pytest

from PyInstaller.compat import is_py2
from PyInstaller.utils.tests import skipif_win, skipif_winorosx, skipif_notwin


def test_ascii_path(pyi_builder):
    distdir = pyi_builder._distdir
    dd_ascii = distdir.encode('ascii', 'replace').decode('ascii')
    if distdir != dd_ascii:
        pytest.skip(reason="Default build path not ASCII, skipping...")

    pyi_builder.test_script('pyi_path_encoding.py')


@skipif_winorosx
def test_linux_non_unicode_path(pyi_builder, monkeypatch):
    # If we set the locale to 'C', mbstowcs should be completely useless. This
    # test verifies that _Py_char2wchar will decode the "undecodable" bytes and
    # will decode even filenames that weren't encoded with the locale encoding.
    distdir = pyi_builder._distdir
    unicode_filename = u'ěščřžýáíé日本語'
    pyi_builder._distdir = os.path.join(distdir, unicode_filename)
    os.makedirs(pyi_builder._distdir)

    tmpdir = os.path.join(pyi_builder._tmpdir, unicode_filename + "_TMP")

    # On py2, os.environ only accepts str
    if is_py2:
        tmpdir = tmpdir.encode(sys.getfilesystemencoding())

    monkeypatch.setenv('LC_ALL', 'C')

    monkeypatch.setenv('TMPDIR', tmpdir)
    monkeypatch.setenv('TMP', tmpdir)

    pyi_builder.test_script('pyi_path_encoding.py')

@skipif_win
def test_osx_linux_unicode_path(pyi_builder, monkeypatch):
    # Mac and Linux should handle 'unicode' type filenames without problem.
    distdir = pyi_builder._distdir
    unicode_filename = u'ěščřžýáíé日本語'
    pyi_builder._distdir = os.path.join(distdir, unicode_filename)
    os.makedirs(pyi_builder._distdir)

    tmpdir = os.path.join(pyi_builder._tmpdir, unicode_filename + "_TMP")

    # On py2, os.environ only accepts str
    if is_py2:
        tmpdir = tmpdir.encode(sys.getfilesystemencoding())

    monkeypatch.setenv('TMPDIR', tmpdir)
    monkeypatch.setenv('TMP', tmpdir)

    pyi_builder.test_script('pyi_path_encoding.py')


@skipif_notwin
def test_win_codepage_path(pyi_builder, monkeypatch):
    distdir = pyi_builder._distdir
    # Create some bytes and decode with the current codepage to get a filename that
    # is guaranteed to encode with the current codepage.
    # Assumes a one-byte codepage, i.e. not cp937 (shift-JIS) which is multibyte
    cp_filename = bytes(bytearray(range(0x80, 0x86))).decode('mbcs')

    pyi_builder._distdir = os.path.join(distdir, cp_filename)
    os.makedirs(pyi_builder._distdir)

    tmpdir = os.path.join(pyi_builder._tmpdir, cp_filename + "_TMP")

    # On py2, os.environ only accepts str
    if is_py2:
        tmpdir = tmpdir.encode(sys.getfilesystemencoding())

    monkeypatch.setenv('TMPDIR', tmpdir)
    monkeypatch.setenv('TMP', tmpdir)

    pyi_builder.test_script('pyi_path_encoding.py')

@skipif_notwin
def test_win_codepage_path_disabled_shortfilename(pyi_builder, monkeypatch):
    distdir = pyi_builder._distdir
    # Create some bytes and decode with the current codepage to get a filename that
    # is guaranteed to encode with the current codepage.
    # Assumes a one-byte codepage, i.e. not cp937 (shift-JIS) which is multibyte
    cp_filename = bytes(bytearray(range(0x80, 0x86))).decode('mbcs')

    distdir = os.path.join(distdir, cp_filename)
    os.makedirs(distdir)

    # Try to remove ShortFileName from this folder using `fsutil`
    # Requires admin privileges, so `xfail` if we don't have them.
    # `8dot3name strip` only affects subfolders, so pass the folder containing
    # our codepage filename
    if is_py2:
        # Python 2 requires mbcs-encoded args to subprocess
        fsutil_distdir = pyi_builder._distdir.encode('mbcs')
    else:
        # Python 3 accepts 'unicode' type.
        fsutil_distdir = pyi_builder._distdir

    if(subprocess.call(['fsutil', '8dot3name', 'strip', fsutil_distdir])):
        pytest.xfail("Administrator privileges required to strip ShortFileName.")

    tmpdir = os.path.join(pyi_builder._tmpdir, cp_filename + "_TMP")

    # On py2, os.environ only accepts str
    if is_py2:
        tmpdir = tmpdir.encode(sys.getfilesystemencoding())

    monkeypatch.setenv('TMPDIR', tmpdir)
    monkeypatch.setenv('TMP', tmpdir)

    pyi_builder._distdir = distdir
    pyi_builder.test_script('pyi_path_encoding.py')


@skipif_notwin
@pytest.mark.xfail(is_py2, reason="Python 2's subprocess.Popen calls CreateProcessA "
                           "which doesn't work with non-codepage paths")
def test_win_non_codepage_path(pyi_builder, monkeypatch):
    # This test is expected to fail on python 2 as it does not have a useful result:
    # On py2 on Windows, subprocess.Popen calls CreateProcessA, which only accepts
    # ANSI codepage-encoded filenames (or SFNs). Encoding non_cp_filename as an SFN
    # will defeat the purpose of this test.
    #
    # To make this test give useful results, we need to use ctypes to call CreateProcessW
    # and replicate most of what the subprocess module does with it (or insert our
    # CreateProcessW into subprocess)
    #
    # To test what happens with a non-ANSI tempdir, we will also need to pass the TMP
    # environ as wide chars.

    distdir = pyi_builder._distdir
    # Both eastern European and Japanese characters - no codepage should encode this.
    non_cp_filename = u'ěščřžýáíé日本語'

    # Codepage encoding would replace some of these chars with "???".

    # On py3, distdir and filename are both str; nothing happens.
    # On py2, distdir is decoded to unicode using ASCII - test fails if
    # tempdir is non-ascii. Shouldn't happen, we're not testing the test system.
    pyi_builder._distdir = os.path.join(distdir, non_cp_filename)
    os.makedirs(pyi_builder._distdir)

    # Note: It is also impossible to pass non-ANSI filenames through environ on Python 2.
    tmpdir = os.path.join(pyi_builder._tmpdir, non_cp_filename + "_TMP")

    monkeypatch.setenv('TMPDIR', tmpdir)
    monkeypatch.setenv('TMP', tmpdir)

    pyi_builder.test_script('pyi_path_encoding.py')

@skipif_notwin
@pytest.mark.skipif(is_py2, reason="Python 3 only.")
def test_win_py3_no_shortpathname(pyi_builder):
    pyi_builder.test_script('pyi_win_py3_no_shortpathname.py')
