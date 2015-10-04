# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Library imports
# ---------------
import glob
import locale
import os
import shutil
import sys
import subprocess

# Third-party imports
# -------------------
import pytest

# Local imports
# -------------
from PyInstaller.compat import architecture, is_darwin, is_win, is_py2
from PyInstaller.utils.tests import importorskip, skipif_win, skipif_winorosx, \
    skipif_notwin, skipif_notosx


def test_run_from_path_environ(pyi_builder):
    pyi_builder.test_script('pyi_absolute_python_path.py', run_from_path=True)


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


def test_distutils_submod(pyi_builder):
    pyi_builder.test_script('pyi_distutils_submod.py')


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


# TODO move 'multiprocessig' tests into 'test_multiprocess.py.


@importorskip('multiprocessing')
def test_multiprocess(pyi_builder):
    pyi_builder.test_script('pyi_multiprocess.py')


@importorskip('multiprocessing')
def test_multiprocess_forking(pyi_builder):
    pyi_builder.test_script('pyi_multiprocess_forking.py')


@importorskip('multiprocessing')
def test_multiprocess_pool(pyi_builder):
    pyi_builder.test_script('pyi_multiprocess_pool.py')


# TODO skip this test if C compiler is not found.
# TODO test it on OS X.
def test_load_dll_using_ctypes(monkeypatch, pyi_builder, compiled_dylib):
    # Note that including the data_dir fixture copies files needed by this test.
    #
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


def test_option_exclude_module(pyi_builder):
    """
    Test to ensure that when using option --exclude-module=xml.sax
    the module 'xml.sax' won't be bundled.
    """
    pyi_builder.test_script('pyi_option_exclude_module.py',
                            pyi_args=['--exclude-module', 'xml.sax'])


@skipif_win
def test_python_makefile(pyi_builder):
    pyi_builder.test_script('pyi_python_makefile.py')


def test_set_icon(pyi_builder, data_dir):
    if is_win:
        args = ['--icon', os.path.join(data_dir.strpath, 'pyi_icon.ico')]
    elif is_darwin:
        # On OS X icon is applied only for windowed mode.
        args = ['--windowed', '--icon', os.path.join(data_dir.strpath, 'pyi_icon.icns')]
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


def test_argument(pyi_builder):
    pyi_builder.test_script('pyi_argument.py', app_args=["--argument"])


@importorskip('win32com')
def test_pywin32_win32com(pyi_builder):
    pyi_builder.test_script('pyi_pywin32_win32com.py')


@importorskip('win32ui')
def test_pywin32_win32ui(pyi_builder):
    pyi_builder.test_script('pyi_pywin32_win32ui.py')


@skipif_notwin
def test_renamed_exe(pyi_builder):
    _old_find_executables = pyi_builder._find_executables
    def _find_executables(name):
        oldexes = _old_find_executables(name)
        newexes = []
        for old in oldexes:

            new = os.path.join(os.path.dirname(old), "renamed_" + os.path.basename(old))
            os.rename(old, new)
            newexes.append(new)
        return newexes

    pyi_builder._find_executables = _find_executables
    pyi_builder.test_script('pyi_helloworld.py')


@skipif_notosx
def test_osx_override_info_plist(pyi_builder_spec):
    pyi_builder_spec.test_spec('pyi_osx_override_info_plist.spec')
