# -*- coding: utf-8 -*-
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

import locale
import os
import sys
import shutil

import pytest

from PyInstaller.compat import is_darwin, is_win
from PyInstaller.utils.tests import importorskip, skipif, skipif_no_compiler, xfail


def test_run_from_path_environ(pyi_builder):
    pyi_builder.test_script('pyi_absolute_python_path.py', run_from_path=True)


@pytest.mark.linux
def test_absolute_ld_library_path(pyi_builder):
    pyi_builder.test_script('pyi_absolute_ld_library_path.py')


def test_absolute_python_path(pyi_builder):
    pyi_builder.test_script('pyi_absolute_python_path.py')


@pytest.mark.linux
@skipif(not os.path.exists('/proc/self/status'), reason='/proc/self/status does not exist')
@pytest.mark.parametrize("symlink_name", ["symlink", "very_long_name_in_symlink", "sub/dir/progam"])
def test_symlink_basename_is_kept(pyi_builder_spec, symlink_name, tmpdir, SPEC_DIR, SCRIPT_DIR):
    def patch(spec_name, symlink_name):
        content = SPEC_DIR.join(spec_name).read_text(encoding="utf-8")
        content = content.replace("@SYMLINKNAME@", symlink_name)
        content = content.replace("@SCRIPTDIR@", str(SCRIPT_DIR))
        outspec = tmpdir.join(spec_name)
        outspec.write_text(content, encoding="utf-8", ensure=True)
        return outspec

    specfile = patch("symlink_basename_is_kept.spec", symlink_name)
    pyi_builder_spec.test_spec(str(specfile), app_name=symlink_name)


def test_pyz_as_external_file(pyi_builder, monkeypatch):
    # This tests the not well documented and seldom used feature of having the PYZ-archive in a separate file (.pkg).

    def MyEXE(*args, **kwargs):
        kwargs['append_pkg'] = False
        return EXE(*args, **kwargs)

    # :todo: find a better way to not even run this test in onefile-mode
    if pyi_builder._mode == 'onefile':
        pytest.skip('only --onedir')

    import PyInstaller.building.build_main
    EXE = PyInstaller.building.build_main.EXE
    monkeypatch.setattr('PyInstaller.building.build_main.EXE', MyEXE)

    pyi_builder.test_source("print('Hello Python!')")


def test_base_modules_regex(pyi_builder):
    """
    Verify that the regex for excluding modules listed in PY3_BASE_MODULES does not exclude other modules.
    """
    pyi_builder.test_source("""
        import resources_testmod
        print('OK')
        """)


def test_celementtree(pyi_builder):
    pyi_builder.test_source("""
        from xml.etree.cElementTree import ElementTree
        print('OK')
        """)


# Test a build with some complexity with the ``noarchive`` debug option.
def test_noarchive(pyi_builder):
    pyi_builder.test_source("from xml.etree.cElementTree import ElementTree", pyi_args=['--debug=noarchive'])


@importorskip('codecs')
def test_codecs(pyi_builder):
    pyi_builder.test_script('pyi_codecs.py')


def test_compiled_filenames(pyi_builder):
    pyi_builder.test_source(
        """
        import pyi_dummy_module
        from os.path import isabs

        assert not isabs(pyi_dummy_module.dummy.__code__.co_filename), (
            "pyi_dummy_module.dummy.__code__.co_filename has compiled filename: %s" %
            (pyi_dummy_module.dummy.__code__.co_filename, )
        )
        assert not isabs(pyi_dummy_module.DummyClass.dummyMethod.__code__.co_filename), (
            "pyi_dummy_module.DummyClass.dummyMethod.__code__.co_filename has compiled filename: %s" %
            (pyi_dummy_module.DummyClass.dummyMethod.__code__.co_filename, )
        )
        """
    )


def test_decoders_ascii(pyi_builder):
    pyi_builder.test_source(
        """
        # Convert type 'bytes' to type 'str'.
        assert b'foo'.decode('ascii') == 'foo'
        """
    )


def test_distutils_submod(pyi_builder):
    # Test import of submodules of distutils package.
    # PyI fails to include `distutils.version` when running from virtualenv.
    pyi_builder.test_source("""
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
        """
    )


def test_email(pyi_builder):
    pyi_builder.test_source(
        """
        from email import utils
        from email.header import Header
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from email.mime.nonmultipart import MIMENonMultipart
        """
    )


@importorskip('tinyaes')
def test_feature_crypto(pyi_builder):
    pyi_builder.test_source(
        """
        from pyimod00_crypto_key import key
        from pyimod02_archive import CRYPT_BLOCK_SIZE

        # Test against issue #1663: importing a package in the bootstrap
        # phase should not interfere with subsequent imports.
        import tinyaes

        assert type(key) is str
        # The test runner uses 'test_key' as key.
        assert key == 'test_key'.zfill(CRYPT_BLOCK_SIZE)
        """,
        pyi_args=['--key=test_key']
    )


def test_feature_nocrypto(pyi_builder):
    pyi_builder.test_source(
        """
        try:
            import pyimod00_crypto_key

            raise AssertionError('The pyimod00_crypto_key module must NOT be there if crypto is disabled.')
        except ImportError:
            pass
        """
    )


def test_filename(pyi_builder):
    pyi_builder.test_script('pyi_filename.py')


def test_getfilesystemencoding(pyi_builder):
    pyi_builder.test_script('pyi_getfilesystemencoding.py')


def test_helloworld(pyi_builder):
    pyi_builder.test_source("print('Hello Python!')")


def test_module__file__attribute(pyi_builder):
    pyi_builder.test_script('pyi_module__file__attribute.py')


def test_module_attributes(tmpdir, pyi_builder):
    # Create file in tmpdir with path to python executable and if it is running in debug mode.
    # Test script uses python interpreter to compare module attributes.
    with open(os.path.join(tmpdir.strpath, 'python_exe.build'), 'w') as f:
        f.write(sys.executable + "\n")
        f.write('debug=%s' % __debug__ + '\n')
        # On Windows we need to preserve systme PATH for subprocesses in tests.
        f.write(os.environ.get('PATH') + '\n')
    pyi_builder.test_script('pyi_module_attributes.py')


def test_module_reload(pyi_builder):
    pyi_builder.test_script('pyi_module_reload.py')


def test_ctypes_hooks_are_in_place(pyi_builder):
    pyi_builder.test_source(
        """
        import ctypes
        assert ctypes.CDLL.__name__ == 'PyInstallerCDLL', ctypes.CDLL
        """
    )


# TODO test it on OS X.
@skipif_no_compiler
def test_load_dll_using_ctypes(monkeypatch, pyi_builder, compiled_dylib):
    # Note that including the data_dir fixture copies files needed by this test.
    #
    # TODO: make sure PyInstaller is able to find the library and bundle it with the app.
    # # If the required dylib does not reside in the current directory, the Analysis class machinery,
    # # based on ctypes.util.find_library, will not find it. This was done on purpose for this test,
    # # to show how to give Analysis class a clue.
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
        """
    )


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
        pyi_args=['--exclude-module', 'xml.sax']
    )


def test_option_verbose(pyi_builder, monkeypatch):
    """
    Test to ensure that option V can be set and has effect.
    """

    # This option is like 'python -v' - trace import statements.
    # 'None' should be allowed or '' also.

    def MyEXE(*args, **kwargs):
        args = list(args)
        args.append([('v', None, 'OPTION')])
        return EXE(*args, **kwargs)

    import PyInstaller.building.build_main
    EXE = PyInstaller.building.build_main.EXE
    monkeypatch.setattr('PyInstaller.building.build_main.EXE', MyEXE)

    pyi_builder.test_source(
        """
        print('test - PYTHONVERBOSE - trace import statements')
        import re # just import anything
        print('test - done')
        """
    )


def test_option_w_unset(pyi_builder):
    """
    Test to ensure that option W is not set by default.
    """
    pyi_builder.test_source("""
        import sys
        assert 'ignore' not in sys.warnoptions
        """)


def test_option_w_ignore(pyi_builder, monkeypatch, capsys):
    """
    Test to ensure that option W can be set.
    """
    def MyEXE(*args, **kwargs):
        args = list(args)
        args.append([('W ignore', '', 'OPTION')])
        return EXE(*args, **kwargs)

    import PyInstaller.building.build_main
    EXE = PyInstaller.building.build_main.EXE
    monkeypatch.setattr('PyInstaller.building.build_main.EXE', MyEXE)

    pyi_builder.test_source("""
        import sys
        assert 'ignore' in sys.warnoptions
        """)

    _, err = capsys.readouterr()
    assert "'import warnings' failed" not in err


@pytest.mark.parametrize("distutils", ["", "from distutils "])
def test_python_makefile(pyi_builder, distutils):
    """
    Tests hooks for ``sysconfig`` and its near-duplicate ``distutils.sysconfig``. Raises an import error if we fail
    to collect the special module that contains the details from pyconfig.h and the Makefile.
    """
    # Ideally we would test that the contents of `sysconfig.get_config_vars()` dict are the same frozen vs. unfrozen,
    # but because some values are paths into a Python installation's guts, these will point into the frozen app when
    # frozen, and therefore not match. Without some fiddly filtering of the paths, this is impossible.

    # As a compromise, test that the dictionary keys are the same to be sure that there is no conditional initialisation
    # of get_config_vars(). I.e., that get_config_vars() does not silently return an empty dictionary if it cannot find
    # the information it needs.
    if distutils:
        from distutils import sysconfig
    else:
        import sysconfig
    unfrozen_keys = sorted(sysconfig.get_config_vars().keys())

    pyi_builder.test_source(
        """
        # The error is raised immediately on import.
        {}import sysconfig

        # But just in case, Python later opt for some lazy loading, force
        # configuration retrieval:
        from pprint import pprint
        pprint(sysconfig.get_config_vars())

        unfrozen_keys = {}
        assert sorted(sysconfig.get_config_vars()) == unfrozen_keys
        """.format(distutils, unfrozen_keys)
    )


def test_set_icon(pyi_builder, data_dir):
    if is_win:
        args = ['--icon', os.path.join(data_dir.strpath, 'pyi_icon.ico')]
    elif is_darwin:
        # On OS X icon is applied only for windowed mode.
        args = ['--windowed', '--icon', os.path.join(data_dir.strpath, 'pyi_icon.icns')]
    else:
        pytest.skip('option --icon works only on Windows and Mac OS X')
    pyi_builder.test_source("print('Hello Python!')", pyi_args=args)


@pytest.mark.win32
def test_invalid_icon(tmpdir, data_dir):
    """
    Ensure a sane error message is given if the user provides a PNG or other unsupported format of image.
    """
    from PyInstaller import PLATFORM, HOMEPATH
    from PyInstaller.utils.win32.icon import CopyIcons

    icon = os.path.join(data_dir.strpath, 'pyi_icon.png')
    bootloader_src = os.path.join(HOMEPATH, 'PyInstaller', 'bootloader', PLATFORM, "run.exe")
    exe = os.path.join(tmpdir, "run.exe")
    shutil.copy(bootloader_src, exe)
    assert os.path.isfile(icon)
    assert os.path.isfile(exe)

    with pytest.raises(
        ValueError, match="path '.*pyi_icon.png' .* not in the correct format.*convert your '.png' file to a '.ico' .*"
    ):
        CopyIcons(exe, icon)


def test_python_home(pyi_builder):
    pyi_builder.test_script('pyi_python_home.py')


def test_stderr_encoding(tmpdir, pyi_builder):
    # NOTE: '-s' option to pytest disables output capturing, changing this test's result:
    # without -s: py.test process changes its own stdout encoding to 'UTF-8' to capture output. subprocess spawned by
    #             py.test has stdout encoding 'cp1252', which is an ANSI codepage. test fails as they do not match.
    # with -s:    py.test process has stdout encoding from windows terminal, which is an OEM codepage. spawned
    #             subprocess has the same encoding. test passes.
    with open(os.path.join(tmpdir.strpath, 'stderr_encoding.build'), 'w') as f:
        if sys.stderr.isatty():
            enc = str(sys.stderr.encoding)
        else:
            # For non-interactive stderr use locale encoding - ANSI codepage.
            # This fixes the test when running with py.test and capturing output.
            enc = locale.getpreferredencoding(False)
        f.write(enc)
    pyi_builder.test_script('pyi_stderr_encoding.py')


def test_stdout_encoding(tmpdir, pyi_builder):
    with open(os.path.join(tmpdir.strpath, 'stdout_encoding.build'), 'w') as f:
        if sys.stdout.isatty():
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
    pyi_builder.test_source("""
        import time
        print(time.strptime(time.ctime()))
        """)


@pytest.mark.darwin
@pytest.mark.linux
def test_time_module_localized(pyi_builder, monkeypatch):
    # This checks that functions 'time.ctime()' and 'time.strptime()' use the same locale. There was an issue with
    # bootloader where every function was using different locale:
    # time.ctime was using 'C'
    # time.strptime was using 'xx_YY' from the environment.
    monkeypatch.setenv('LC_ALL', 'cs_CZ.UTF-8')
    pyi_builder.test_source("""
        import time
        print(time.strptime(time.ctime()))
        """)


def test_xmldom_module(pyi_builder):
    pyi_builder.test_source(
        """
        print('Importing xml.dom')
        from xml.dom import pulldom
        print('Importing done')
        """
    )


def test_threading_module(pyi_builder):
    pyi_builder.test_source(
        """
        import threading
        import sys

        print('See stderr for messages')
        def print_(*args): print(*args, file=sys.stderr)

        def doit(nm):
            print_(nm, 'started')
            import pyi_testmod_threading
            try:
                print_(nm, pyi_testmod_threading.x)
            finally:
                print_(nm, pyi_testmod_threading)

        t1 = threading.Thread(target=doit, args=('t1',))
        t2 = threading.Thread(target=doit, args=('t2',))
        t1.start()
        t2.start()
        doit('main')
        t1.join() ; print_('t1 joined')
        t2.join() ; print_('t2 joined')
        print_('finished.')
        """
    )


def test_threading_module2(pyi_builder):
    pyi_builder.test_script('pyi_threading_module2.py')


def test_argument(pyi_builder):
    pyi_builder.test_source(
        """
        import sys
        assert sys.argv[1] == "--argument", "sys.argv[1] was %r, expected %r" % (sys.argv[1], "--argument")
        """,
        app_args=["--argument"]
    )


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
        """
    )


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
        """
    )


@importorskip('win32ui')
@xfail(reason="https://github.com/mhammond/pywin32/issues/1614")
def test_pywin32_win32ui(pyi_builder):
    pyi_builder.test_source(
        """
        # Test importing some modules from pywin32 package.
        # All modules from pywin32 depens on module pywintypes.
        # This module should be also included.
        import win32ui
        from pywin.mfc.dialog import Dialog
        d = Dialog(win32ui.IDD_SIMPLE_INPUT)
        """
    )


@pytest.mark.win32
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


def test_spec_with_utf8(pyi_builder_spec):
    pyi_builder_spec.test_spec('spec-with-utf8.spec')


@pytest.mark.darwin
def test_osx_override_info_plist(pyi_builder_spec):
    pyi_builder_spec.test_spec('pyi_osx_override_info_plist.spec')


def test_hook_collect_submodules(pyi_builder, script_dir):
    # This is designed to test the operation of PyInstaller.utils.hook.collect_submodules. To do so:
    #
    # 1. It imports the dummy module pyi_collect_submodules_mod, which contains nothing.
    # 2. This causes hook-pyi_collect_submodules_mod.py to be run, which collects some dummy submodules. In this case,
    #    it collects from modules/pyi_testmod_relimp.
    # 3. Therefore, we should be able to find hidden imports under pyi_testmod_relimp.
    pyi_builder.test_source(
        """
        import pyi_collect_submodules_mod
        __import__('pyi_testmod_relimp.B.C')
        """, ['--additional-hooks-dir=%s' % script_dir.join('pyi_hooks')]
    )


# Test that PyInstaller can handle a script with an arbitrary extension.
def test_arbitrary_ext(pyi_builder):
    pyi_builder.test_script('pyi_arbitrary_ext.foo')


def test_option_runtime_tmpdir(pyi_builder):
    """
    Test to ensure that option `runtime_tmpdir` can be set and has effect.
    """

    pyi_builder.test_source(
        """
        print('test - runtime_tmpdir - custom runtime temporary directory')
        import os
        import sys

        cwd = os.path.abspath(os.getcwd())
        runtime_tmpdir = os.path.abspath(sys._MEIPASS)
        # for onedir mode, runtime_tmpdir == cwd
        # for onefile mode, os.path.dirname(runtime_tmpdir) == cwd
        if not runtime_tmpdir == cwd and not os.path.dirname(runtime_tmpdir) == cwd:
            raise SystemExit('Expected sys._MEIPASS to be under current working dir.'
                             ' sys._MEIPASS = ' + runtime_tmpdir + ', cwd = ' + cwd)
        print('test - done')
        """, ['--runtime-tmpdir=.']
    )  # set runtime-tmpdir to current working dir


@xfail(reason='Issue #3037 - all scripts share the same global vars')
def test_several_scripts1(pyi_builder_spec):
    """
    Verify each script has it's own global vars (original case, see issue #2949).
    """
    pyi_builder_spec.test_spec('several-scripts1.spec')


@xfail(reason='Issue #3037 - all scripts share the same global vars')
def test_several_scripts2(pyi_builder_spec):
    """
    Verify each script has it's own global vars (basic test).
    """
    pyi_builder_spec.test_spec('several-scripts2.spec')


@pytest.mark.win32
def test_pe_checksum(pyi_builder):
    import ctypes
    from ctypes import wintypes

    pyi_builder.test_source("print('hello')")
    exes = pyi_builder._find_executables('test_source')
    assert exes
    for exe in exes:
        # Validate the PE checksum using the official Windows API for doing so.
        # https://docs.microsoft.com/en-us/windows/win32/api/imagehlp/nf-imagehlp-mapfileandchecksumw
        header_sum = wintypes.DWORD()
        checksum = wintypes.DWORD()
        assert ctypes.windll.imagehlp.MapFileAndCheckSumW(
            ctypes.c_wchar_p(exe), ctypes.byref(header_sum), ctypes.byref(checksum)
        ) == 0

        assert header_sum.value == checksum.value


def test_onefile_longpath(pyi_builder, tmpdir):
    """
    Verify that files with paths longer than 260 characters are correctly extracted from the onefile build.
    See issue #5615."
    """
    # The test is relevant only for onefile builds
    if pyi_builder._mode != 'onefile':
        pytest.skip('The test is relevant only to onefile builds.')
    # Create data file with secret
    _SECRET = 'LongDataPath'
    src_filename = tmpdir / 'data.txt'
    with open(src_filename, 'w') as fp:
        fp.write(_SECRET)
    # Generate long target filename/path; eight equivalents of SHA256 strings plus data.txt should push just the
    # _MEIPASS-relative path beyond 260 characters...
    dst_filename = os.path.join(*[32 * chr(c) for c in range(ord('A'), ord('A') + 8)], 'data.txt')
    assert len(dst_filename) >= 260
    # Name for --add-data
    if is_win:
        add_data_name = src_filename + ';' + os.path.dirname(dst_filename)
    else:
        add_data_name = src_filename + ':' + os.path.dirname(dst_filename)

    pyi_builder.test_source(
        """
        import sys
        import os

        data_file = os.path.join(sys._MEIPASS, r'{data_file}')
        print("Reading secret from %r" % (data_file))
        with open(data_file, 'r') as fp:
            secret = fp.read()
        assert secret == r'{secret}'
        """.format(data_file=dst_filename, secret=_SECRET), ['--add-data', str(add_data_name)]
    )


@pytest.mark.win32
@pytest.mark.parametrize("icon", ["icon_default", "icon_none", "icon_given"])
def test_onefile_has_manifest(pyi_builder, icon):
    """
    Verify that onefile builds on Windows end up having manifest embedded. See issue #5624.
    """
    from PyInstaller.utils.win32 import winmanifest
    from PyInstaller import PACKAGEPATH

    # The test is relevant only for onefile builds
    if pyi_builder._mode != 'onefile':
        pytest.skip('The test is relevant only to onefile builds.')
    # Icon type
    if icon == 'icon_default':
        # Default; no --icon argument
        extra_args = []
    elif icon == 'icon_none':
        # Disable icon completely; --icon NONE
        extra_args = ['--icon', 'NONE']
    elif icon == 'icon_given':
        # Locate pyinstaller's default icon, and explicitly give it
        # via --icon argument
        icon_path = os.path.join(PACKAGEPATH, 'bootloader', 'images', 'icon-console.ico')
        extra_args = ['--icon', icon_path]
    # Build the executable...
    pyi_builder.test_source("""print('Hello world!')""", extra_args)
    # ... and ensure that it contains manifest
    exes = pyi_builder._find_executables('test_source')
    assert exes
    for exe in exes:
        res = winmanifest.GetManifestResources(exe)
        assert res, "No manifest resources found!"


@pytest.mark.parametrize("append_pkg", [True, False], ids=["embedded", "sideload"])
def test_sys_executable(pyi_builder, append_pkg, monkeypatch):
    """
    Verify that sys.executable points to the executable, regardless of build mode (onedir vs. onefile) and the
    append_pkg setting (embedded vs. side-loaded CArchive PKG).
    """
    # Set append_pkg; taken from test_pyz_as_external_file
    import PyInstaller.building.build_main
    EXE = PyInstaller.building.build_main.EXE

    def MyEXE(*args, **kwargs):
        kwargs['append_pkg'] = append_pkg
        return EXE(*args, **kwargs)

    monkeypatch.setattr('PyInstaller.building.build_main.EXE', MyEXE)

    # Expected executable basename
    exe_basename = 'test_source'
    if is_win:
        exe_basename += '.exe'

    pyi_builder.test_source(
        """
        import sys
        import os
        exe_basename = os.path.basename(sys.executable)
        assert exe_basename == '{}', "Unexpected basename(sys.executable): " + exe_basename
        """.format(exe_basename)
    )


@pytest.mark.win32
def test_subprocess_in_windowed_mode(pyi_windowed_builder):
    """Test invoking subprocesses from a PyInstaller app built in windowed mode."""

    pyi_windowed_builder.test_source(
        r"""
        from subprocess import PIPE, run
        from unittest import TestCase

        # Lazily use unittest's rich assertEqual() for assertions with builtin diagnostics.
        assert_equal = TestCase().assertEqual

        run([{0}, "-c", ""], check=True)

        # Verify that stdin, stdout and stderr still work and haven't been muddled.
        p = run([{0}, "-c", "print('foo')"], stdout=PIPE, universal_newlines=True)
        assert_equal(p.stdout, "foo\n", p.stdout)

        p = run([{0}, "-c", r"import sys; sys.stderr.write('bar\n')"], stderr=PIPE, universal_newlines=True)
        assert_equal(p.stderr, "bar\n", p.stderr)

        p = run([{0}], input="print('foo')\nprint('bar')\n", stdout=PIPE, universal_newlines=True)
        assert_equal(p.stdout, "foo\nbar\n", p.stdout)
        """.format(repr(sys.executable)),
        pyi_args=["--windowed"]
    )
