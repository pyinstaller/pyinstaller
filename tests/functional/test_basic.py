# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import glob
import locale
import os
import shutil
import sys
import subprocess

import pytest

from PyInstaller.compat import architecture, is_darwin, is_win, is_py2
from PyInstaller.utils.tests import importorskip, skipif_win, skipif_winorosx, \
    xfail_py2, skipif_notwin

# Directory with data for some tests.
_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


@skipif_winorosx
def test_absolute_ld_library_path(pyi_builder):
    pyi_builder.test_script('pyi_absolute_ld_library_path.py')


def test_absolute_python_path(pyi_builder):
    pyi_builder.test_script('pyi_absolute_python_path.py')


def test_celementtree(pyi_builder):
    pyi_builder.test_script('pyi_celementtree.py')


@importorskip('codecs')
def test_codecs(pyi_builder):
    pyi_builder.test_script('pyi_codecs.py')


def test_decoders_ascii(pyi_builder):
    pyi_builder.test_script('pyi_decoders_ascii.py')


def test_dynamic_module(pyi_builder):
    pyi_builder.test_script('pyi_dynamic_module.py')


def test_email(pyi_builder):
    pyi_builder.test_script('pyi_email.py')


@importorskip('Crypto')
def test_feature_crypto(pyi_builder):
    pyi_builder.test_script('pyi_feature_crypto.py', pyi_args=['--key=test_key'])


def test_feature_nocrypto(pyi_builder):
    pyi_builder.test_script('pyi_feature_nocrypto.py')


def test_filename(pyi_builder):
    pyi_builder.test_script('pyi_filename.py')


def test_getfilesystemencoding(pyi_builder):
    pyi_builder.test_script('pyi_getfilesystemencoding.py')


def test_helloworld(pyi_builder):
    pyi_builder.test_script('pyi_helloworld.py')


def test_module__file__attribute(pyi_builder):
    pyi_builder.test_script('pyi_module__file__attribute.py')


def test_module_attributes(tmpdir, pyi_builder):
    # Create file in tmpdir with path to python executable and if it is running
    # in debug mode.
    # Test script uses python interpreter to compare module attributes.
    with open(os.path.join(tmpdir.strpath, 'python_exe.build'), 'w') as f:
        f.write(sys.executable + "\n")
        f.write('debug=%s' % __debug__ + '\n')
        # On Windows we need to preserve systme PATH for subprocesses in tests.
        f.write(os.environ.get('PATH') + '\n')
    pyi_builder.test_script('pyi_module_attributes.py')


def test_module_reload(pyi_builder):
    pyi_builder.test_script('pyi_module_reload.py')


@importorskip('multiprocessing')
def test_multiprocess(pyi_builder):
    pyi_builder.test_script('pyi_multiprocess.py')


@importorskip('multiprocessing')
def test_multiprocess_forking(pyi_builder):
    pyi_builder.test_script('pyi_multiprocess_forking.py')


# TODO skip this test if C compiler is not found.
# TODO test it on OS X.
def test_load_dll_using_ctypes(tmpdir, monkeypatch, pyi_builder):
    # Copy code for 'ctypes_dylib' into tmpdir.
    src = os.path.join(_DATA_DIR, 'ctypes_dylib')
    dst = tmpdir.strpath
    files = glob.glob(src + '/*.c')
    for f in files:
        shutil.copy(f, dst)

    # Compile the ctypes_dylib there.
    monkeypatch.chdir(dst)  # Make dst the CWD directory.
    if is_win:
        # For Mingw-x64 we must pass '-m32' to build 32-bit binaries
        march = '-m32' if architecture() == '32bit' else '-m64'
        ret = subprocess.call('gcc -shared ' + march + ' ctypes_dylib.c -o ctypes_dylib.dll', shell=True)
        if ret != 0:
            # Find path to cl.exe file.
            from distutils.msvccompiler import MSVCCompiler
            comp = MSVCCompiler()
            comp.initialize()
            cl_path = comp.cc
            # Fallback to msvc.
            ret = subprocess.call([cl_path, '/LD', 'ctypes_dylib.c'], shell=False)
    elif is_darwin:
        # On Mac OS X we need to detect architecture - 32 bit or 64 bit.
        arch = 'i386' if architecture() == '32bit' else 'x86_64'
        cmd = ('gcc -arch ' + arch + ' -Wall -dynamiclib '
            'ctypes_dylib.c -o ctypes_dylib.dylib -headerpad_max_install_names')
        ret = subprocess.call(cmd, shell=True)
        id_dylib = os.path.abspath('ctypes_dylib.dylib')
        ret = subprocess.call('install_name_tool -id %s ctypes_dylib.dylib' % (id_dylib,), shell=True)
    else:
        ret = subprocess.call('gcc -fPIC -shared ctypes_dylib.c -o ctypes_dylib.so', shell=True)
    assert ret == 0, 'Compile ctypes_dylib failed.'
    # Reset the CWD directory.
    monkeypatch.undo()

    # TODO Make sure PyInstaller is able to find the library and bundle it with the app.
    # # If the required dylib does not reside in the current directory, the Analysis
    # # class machinery, based on ctypes.util.find_library, will not find it. This
    # # was done on purpose for this test, to show how to give Analysis class
    # # a clue.
    # if is_win:
    #     os.environ['PATH'] = os.path.abspath(CTYPES_DIR) + ';' + os.environ['PATH']
    # else:
    #     os.environ['LD_LIBRARY_PATH'] = CTYPES_DIR
    #     os.environ['DYLD_LIBRARY_PATH'] = CTYPES_DIR
    #     os.environ['LIBPATH'] = CTYPES_DIR

    # Build and run the app.
    pyi_builder.test_script('pyi_load_dll_using_ctypes.py')


def test_get_meipass_value(pyi_builder):
    pyi_builder.test_script('pyi_get_meipass_value.py')


def test_chdir_meipass(pyi_builder):
    pyi_builder.test_script('pyi_chdir_meipass.py')


@skipif_win
@pytest.mark.xfail(reason='failing when running in Travis')
def test_python_makefile(pyi_builder):
    pyi_builder.test_script('pyi_python_makefile.py')


def test_set_icon(pyi_builder):
    icon_dir = os.path.join(_DATA_DIR, 'icons')
    if is_win:
        args = ['--icon', os.path.join(icon_dir, 'pyi_icon.ico')]
    elif is_darwin:
        # On OS X icon is applied only for windowed mode.
        args = ['--windowed', '--icon', os.path.join(icon_dir, 'pyi_icon.icns')]
    else:
        pytest.skip('option --icon works only on Windows and Mac OS X')
    # Just use helloworld script.
    pyi_builder.test_script('pyi_helloworld.py', pyi_args=args)


def test_python_home(pyi_builder):
    pyi_builder.test_script('pyi_python_home.py')


def test_stderr_encoding(tmpdir, pyi_builder):
    # NOTE: '-s' option to pytest disables output capturing, changing this test's result:
    # without -s: py.test process changes its own stdout encoding to 'UTF-8' to
    #             capture output. subprocess spawned by py.test has stdout encoding
    #             'cp1252', which is an ANSI codepage. test fails as they do not match.
    # with -s:    py.test process has stdout encoding from windows terminal, which is an
    #             OEM codepage. spawned subprocess has the same encoding. test passes.
    #
    with open(os.path.join(tmpdir.strpath, 'stderr_encoding.build'), 'w') as f:
        if is_py2:
            if sys.stderr.isatty() and is_win:
                enc = str(sys.stderr.encoding)
            else:
                # In Python 2 on Mac OS X and Linux 'sys.stderr.encoding' is set to None.
                # On Windows when running in non-interactive terminal it is None.
                enc = 'None'
        elif sys.stderr.isatty():
            enc = str(sys.stderr.encoding)
        else:
            # For non-interactive stderr use locale encoding - ANSI codepage.
            # This fixes the test when running with py.test and capturing output.
            enc = locale.getpreferredencoding(False)
        f.write(enc)
    pyi_builder.test_script('pyi_stderr_encoding.py')


def test_stdout_encoding(tmpdir, pyi_builder):
    with open(os.path.join(tmpdir.strpath, 'stdout_encoding.build'), 'w') as f:
        if is_py2:
            if sys.stdout.isatty() and is_win:
                enc = str(sys.stdout.encoding)
            else:
                # In Python 2 on Mac OS X and Linux 'sys.stdout.encoding' is set to None.
                # On Windows when running in non-interactive terminal it is None.
                enc = 'None'
        elif sys.stdout.isatty():
            enc = str(sys.stdout.encoding)
        else:
            # For non-interactive stderr use locale encoding - ANSI codepage.
            # This fixes the test when running with py.test and capturing output.
            enc = locale.getpreferredencoding(False)
        f.write(enc)
    pyi_builder.test_script('pyi_stdout_encoding.py')


def test_site_module_disabled(pyi_builder):
    pyi_builder.test_script('pyi_site_module_disabled.py')


def test_time_module(pyi_builder):
    pyi_builder.test_script('pyi_time_module.py')


@skipif_win
def test_time_module_localized(pyi_builder, monkeypatch):
    # This checks that functions 'time.ctime()' and 'time.strptime()'
    # use the same locale. There was an issue with bootloader where
    # every function was using different locale:
    # time.ctime was using 'C'
    # time.strptime was using 'xx_YY' from the environment.
    lang = 'cs_CZ' if is_darwin else 'cs_CZ.UTF-8'
    monkeypatch.setenv('LC_ALL', lang)
    pyi_builder.test_script('pyi_time_module.py')


def test_xmldom_module(pyi_builder):
    pyi_builder.test_script('pyi_xmldom_module.py')


def test_threading_module(pyi_builder):
    pyi_builder.test_script('pyi_threading_module.py')


@importorskip('win32com')
def test_pywin32_win32com(pyi_builder):
    pyi_builder.test_script('pyi_pywin32_win32com.py')


@importorskip('win32ui')
def test_pywin32_win32ui(pyi_builder):
    pyi_builder.test_script('pyi_pywin32_win32ui.py')


def test_ascii_path(pyi_builder):
    distdir = pyi_builder._distdir
    dd_ascii = distdir.encode('ascii', 'replace').decode('ascii')
    if distdir != dd_ascii:
        pytest.skip(reason="Default build path not ASCII, skipping...")

    pyi_builder.test_script('pyi_path_encoding.py')

@skipif_win
def test_osx_linux_unicode_path(pyi_builder):
    # Mac and Linux should handle 'unicode' type filenames without problem.
    distdir = pyi_builder._distdir
    unicode_filename = u'ěščřžýáíé日本語'
    pyi_builder._distdir = os.path.join(distdir, unicode_filename)
    os.makedirs(pyi_builder._distdir)

    pyi_builder.test_script('pyi_path_encoding.py')


@skipif_notwin
def test_win_codepage_path(pyi_builder):
    distdir = pyi_builder._distdir
    # Create some bytes and decode with the current codepage to get a filename that
    # is guaranteed to encode with the current codepage.
    # Assumes a one-byte codepage, i.e. not cp937 (shift-JIS) which is multibyte
    cp_filename = bytes(bytearray(range(0x80, 0x86))).decode('mbcs')

    pyi_builder._distdir = os.path.join(distdir, cp_filename)
    os.makedirs(pyi_builder._distdir)

    pyi_builder.test_script('pyi_path_encoding.py')


if is_py2:
    _noncp_path_reason = "Python 2's subprocess.Popen calls CreateProcessA which "\
                         "doesn't work with non-codepage paths"
else:
    _noncp_path_reason = "Bootloader sets sys.argv using ANSI argv on Python 3"

@skipif_notwin
@pytest.mark.xfail(reason=_noncp_path_reason)
def test_win_non_codepage_path(pyi_builder):
    # This test is expected to fail on python 2 as it does not have a useful result:
    # On py2 on Windows, subprocess.Popen calls CreateProcessA, which only accepts
    # ANSI codepage-encoded filenames (or SFNs). Encoding non_cp_filename as an SFN
    # will defeat the purpose of this test.
    #
    # To make this test give useful results, we need to use ctypes to call CreateProcessW
    # and replicate most of what the subprocess module does with it (or insert our
    # CreateProcessW into subprocess)

    distdir = pyi_builder._distdir
    # Both eastern European and Japanese characters - no codepage should encode this.
    non_cp_filename = u'ěščřžýáíé日本語'

    # Codepage encoding would replace some of these chars with "???".

    # On py3, distdir and filename are both str; nothing happens.
    # On py2, distdir is decoded to unicode using ASCII - test fails if
    # tempdir is non-ascii. Shouldn't happen, we're not testing the test system.
    pyi_builder._distdir = os.path.join(distdir, non_cp_filename)
    os.makedirs(pyi_builder._distdir)

    pyi_builder.test_script('pyi_path_encoding.py')

"""
def test_(pyi_builder):
    pyi_builder.test_script('')
"""
