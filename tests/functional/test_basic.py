#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import glob
import os
import shutil
import sys
import subprocess

import pytest

from PyInstaller.compat import architecture, is_darwin, is_win
from PyInstaller.utils.tests import importorskip, skipif_win, skipif_winorosx


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


@pytest.mark.xfail(reason='failing with Python 3.3 in Appveyor')
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


@pytest.mark.xfail(reason='failing with Python 3.3 in Travis')
def test_module_reload(pyi_builder):
    pyi_builder.test_script('pyi_module_reload.py')


@importorskip('multiprocessing')
def test_multiprocess(pyi_builder):
    pyi_builder.test_script('pyi_multiprocess.py')


@importorskip('multiprocessing')
def test_multiprocess_forking(pyi_builder):
    pyi_builder.test_script('pyi_multiprocess_forking.py')


# TODO skip this test if C compiler is not found.
# TODO test it on Windows and OS X.
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
        ret = subprocess.call('gcc -shared ctypes_dylib.c -o ctypes_dylib.dll', shell=True)
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
        icon = ['--windowed', '--icon', os.path.join(icon_dir, 'pyi_icon.icns')]
    else:
        pytest.skip('option --icon works only on Windows and Mac OS X')
    # Just use helloworld script.
    pyi_builder.test_script('pyi_helloworld.py', pyi_args=args)


def test_python_home(pyi_builder):
    pyi_builder.test_script('pyi_python_home.py')


def test_stderr_encoding(pyi_builder):
    pyi_builder.test_script('pyi_stderr_encoding.py')


def test_stdout_encoding(pyi_builder):
    pyi_builder.test_script('pyi_stdout_encoding.py')


def test_site_module_disabled(pyi_builder):
    pyi_builder.test_script('pyi_site_module_disabled.py')


def test_time_module(pyi_builder):
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


"""
def test_(pyi_builder):
    pyi_builder.test_script('')
"""
