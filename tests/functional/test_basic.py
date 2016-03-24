# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2005-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Library imports
# ---------------
import locale
import os
import sys

# Third-party imports
# -------------------
import pytest

# Local imports
# -------------
from PyInstaller.compat import is_darwin, is_win, is_py2
from PyInstaller.utils.tests import importorskip, skipif_win, skipif_winorosx, \
    skipif_notwin, skipif_notosx, xfail


def test_run_from_path_environ(pyi_builder):
    pyi_builder.test_script('pyi_absolute_python_path.py', run_from_path=True)


@skipif_winorosx
def test_absolute_ld_library_path(pyi_builder):
    pyi_builder.test_script('pyi_absolute_ld_library_path.py')


def test_absolute_python_path(pyi_builder):
    pyi_builder.test_script('pyi_absolute_python_path.py')


def test_pyz_as_external_file(pyi_builder, monkeypatch):
    # This tests the not well documented and seldom used feature of
    # having the PYZ-archive in a separate file (.pkg).

    def MyEXE(*args, **kwargs):
        kwargs['append_pkg'] = False
        return EXE(*args, **kwargs)

    # :todo: find a better way to not even run this test in ondir-mode
    if pyi_builder._mode == 'onefile':
        pytest.skip('only --onedir')

    import PyInstaller
    EXE = PyInstaller.building.build_main.EXE
    monkeypatch.setattr('PyInstaller.building.build_main.EXE', MyEXE)

    pyi_builder.test_source("print('Hello Python!')")

def test_base_modules_regex(pyi_builder):
    """
    Verify that the regex for excluding modules listed in
    PY3_BASE_MODULES does not exclude other modules.
    """
    pyi_builder.test_source(
        """
        import resources_testmod
        print('OK')
        """)


def test_celementtree(pyi_builder):
    pyi_builder.test_source(
        """
        from xml.etree.cElementTree import ElementTree
        print('OK')
        """)

@importorskip('codecs')
def test_codecs(pyi_builder):
    pyi_builder.test_script('pyi_codecs.py')


def test_compiled_filenames(pyi_builder):
    pyi_builder.test_source("""
    import pyi_dummy_module
    from os.path import isabs

    assert not isabs(pyi_dummy_module.dummy.__code__.co_filename), "pyi_dummy_module.dummy.__code__.co_filename has compiled filename: %s" % (pyi_dummy_module.dummy.__code__.co_filename,)
    assert not isabs(pyi_dummy_module.DummyClass.dummyMethod.__code__.co_filename), "pyi_dummy_module.DummyClass.dummyMethod.__code__.co_filename has compiled filename: %s" % (pyi_dummy_module.DummyClass.dummyMethod.__code__.co_filename,)
    """)

def test_decoders_ascii(pyi_builder):
    pyi_builder.test_source(
        """
        # This import forces Python 2 to handle string as unicode -
        # as with prefix 'u'.
        from __future__ import unicode_literals

        # Convert type 'bytes' to type 'str' (Py3) or 'unicode' (Py2).
        assert b'foo'.decode('ascii') == 'foo'
        """)


def test_distutils_submod(pyi_builder):
    # Test import of submodules of distutils package
    # PyI fails to include `distutils.version` when running from virtualenv
    pyi_builder.test_source(
        """
        from distutils.version import LooseVersion
        """)


def test_dynamic_module(pyi_builder):
    pyi_builder.test_source(
        """
        import pyi_testmod_dynamic

        # The value 'foo' should  not be None.
        print("'foo' value: %s" % pyi_testmod_dynamic.foo)
        assert pyi_testmod_dynamic.foo is not None
        assert pyi_testmod_dynamic.foo == 'A new value!'
        """)


def test_email(pyi_builder):
    # Test import of new-style email module names.
    # This should work on Python 2.5+
    pyi_builder.test_source(
        """
        from email import utils
        from email.header import Header
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from email.mime.nonmultipart import MIMENonMultipart
        """)

@importorskip('Crypto')
def test_feature_crypto(pyi_builder):
    pyi_builder.test_source(
        """
        from pyimod00_crypto_key import key
        from pyimod02_archive import CRYPT_BLOCK_SIZE

        # Issue 1663: Crypto feature caused issues when using PyCrypto module.
        import Crypto.Cipher.AES

        assert type(key) is str
        # The test runner uses 'test_key' as key.
        assert key == 'test_key'.zfill(CRYPT_BLOCK_SIZE)
        """,
        pyi_args=['--key=test_key'])


def test_feature_nocrypto(pyi_builder):
    pyi_builder.test_source(
        """
        try:
            import pyimod00_crypto_key

            raise AssertionError('The pyimod00_crypto_key module must NOT be there if crypto is disabled.')
        except ImportError:
            pass
        """)


def test_filename(pyi_builder):
    pyi_builder.test_script('pyi_filename.py')


def test_getfilesystemencoding(pyi_builder):
    pyi_builder.test_script('pyi_getfilesystemencoding.py')


def test_helloworld(pyi_builder):
    pyi_builder.test_source("print('Hello Python!')")


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


@xfail(is_darwin, reason='Issue #1895.')
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
    # Ensure meipass dir exists.
    pyi_builder.test_source(
        """
        import os, sys
        os.chdir(sys._MEIPASS)
        print(os.getcwd())
        """)


def test_option_exclude_module(pyi_builder):
    """
    Test to ensure that when using option --exclude-module=xml.sax
    the module 'xml.sax' won't be bundled.
    """
    pyi_builder.test_source(
        """
        try:
            import xml.sax
            # Option --exclude-module=xml.sax did not work and the module
            # was successfully imported.
            raise SystemExit('Module xml.sax was excluded but it is '
                             'bundled with the executable.')
        except ImportError:
            # The Import error is expected since PyInstaller should
            # not bundle 'xml.sax' module.
            pass
        """,
        pyi_args=['--exclude-module', 'xml.sax'])


def test_option_verbose(pyi_builder, monkeypatch):
    "Test to ensure that option V can be set and has effect."
    # This option is like 'python -v' - trace import statements.
    # 'None' should be allowed or '' also.

    def MyEXE(*args, **kwargs):
        args = list(args)
        args.append([('v', None, 'OPTION')])
        return EXE(*args, **kwargs)

    import PyInstaller
    EXE = PyInstaller.building.build_main.EXE
    monkeypatch.setattr('PyInstaller.building.build_main.EXE', MyEXE)

    pyi_builder.test_source(
        """
        print('test - PYTHONVERBOSE - trace import statements')
        import re # just import anything
        print('test - done')
        """)


def test_option_w_unset(pyi_builder):
    "Test to ensure that option W is not set by default."
    pyi_builder.test_source(
        """
        import sys
        assert 'ignore' not in sys.warnoptions
        """)

def test_option_w_ignore(pyi_builder, monkeypatch):
    "Test to ensure that option W can be set."

    def MyEXE(*args, **kwargs):
        args = list(args)
        args.append([('W ignore', '', 'OPTION')])
        return EXE(*args, **kwargs)

    import PyInstaller
    EXE = PyInstaller.building.build_main.EXE
    monkeypatch.setattr('PyInstaller.building.build_main.EXE', MyEXE)

    pyi_builder.test_source(
        """
        import sys
        assert 'ignore' in sys.warnoptions
        """)


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
    pyi_builder.test_source("print('Hello Python!')", pyi_args=args)


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
    pyi_builder.test_source(
        """
        import time
        print(time.strptime(time.ctime()))
        """)


@skipif_win
def test_time_module_localized(pyi_builder, monkeypatch):
    # This checks that functions 'time.ctime()' and 'time.strptime()'
    # use the same locale. There was an issue with bootloader where
    # every function was using different locale:
    # time.ctime was using 'C'
    # time.strptime was using 'xx_YY' from the environment.
    lang = 'cs_CZ' if is_darwin else 'cs_CZ.UTF-8'
    monkeypatch.setenv('LC_ALL', lang)
    pyi_builder.test_source(
        """
        import time
        print(time.strptime(time.ctime()))
        """)


def test_xmldom_module(pyi_builder):
    pyi_builder.test_source(
        """
        print('Importing xml.dom')
        from xml.dom import pulldom
        print('Importing done')
        """)


def test_threading_module(pyi_builder):
    pyi_builder.test_source(
        """
        import threading

        def doit(nm):
            print(('%s started' % nm))
            import pyi_testmod_threading
            print(('%s %s' % (nm, pyi_testmod_threading.x)))

        t1 = threading.Thread(target=doit, args=('t1',))
        t2 = threading.Thread(target=doit, args=('t2',))
        t1.start()
        t2.start()
        doit('main')
        t1.join()
        t2.join()
        """)


def test_threading_module2(pyi_builder):
    pyi_builder.test_script('pyi_threading_module2.py')


def test_argument(pyi_builder):
    pyi_builder.test_source(
        '''
        import sys
        assert sys.argv[1] == "--argument", "sys.argv[1] was %s, expected %r" % (sys.argv[1], "--argument")
        ''',
        app_args=["--argument"])


@importorskip('win32com')
def test_pywin32_win32com(pyi_builder):
    pyi_builder.test_source(
        """
        # Test importing some modules from pywin32 package.
        # All modules from pywin32 depens on module pywintypes.
        # This module should be also included.
        import win32com
        import win32com.client
        import win32com.server
        """)


#@pytest.mark.xfail(reason="Requires post-create-package hooks (issue #1322)")
@importorskip('win32com')
def test_pywin32_comext(pyi_builder):
    pyi_builder.test_source(
        """
        # Test importing modules from win32com that are actually present in
        # win32comext, and made available by __path__ changes in win32com.
        from win32com.shell import shell
        from win32com.propsys import propsys
        from win32com.bits import bits
        """)


@importorskip('win32ui')
def test_pywin32_win32ui(pyi_builder):
    pyi_builder.test_source(
        """
        # Test importing some modules from pywin32 package.
        # All modules from pywin32 depens on module pywintypes.
        # This module should be also included.
        import win32ui
        from pywin.mfc.dialog import Dialog
        d = Dialog(win32ui.IDD_SIMPLE_INPUT)
        """)


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
    pyi_builder.test_source("print('Hello Python!')")


@skipif_notosx
def test_osx_override_info_plist(pyi_builder_spec):
    pyi_builder_spec.test_spec('pyi_osx_override_info_plist.spec')

def test_hook_collect_submodules(pyi_builder, script_dir):
    # This is designed to test the operation of
    # PyInstaller.utils.hook.collect_submodules. To do so:
    #
    # 1. It imports the dummy module pyi_collect_submodules_mod, which
    #    contains nothing.
    # 2. This causes hook-pyi_collect_submodules_mod.py to be run,
    #    which collects some dummy submodules. In this case, it
    #    collects from modules/pyi_testmod_relimp.
    # 3. Therefore, we should be able to find hidden imports under
    #    pyi_testmod_relimp.
    pyi_builder.test_source(
        """
        import pyi_collect_submodules_mod
        __import__('pyi_testmod_relimp.B.C')
        """,
        ['--additional-hooks-dir=%s' % script_dir.join('pyi_hooks')])
