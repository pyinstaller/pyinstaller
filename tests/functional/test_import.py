# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import os
import glob
import ctypes
import ctypes.util

import pytest

from PyInstaller.compat import is_darwin, is_py2, is_py3, is_py35, is_win
from PyInstaller.utils.tests import skipif, importorskip, \
    skipif_notwin, skipif_no_compiler, xfail, has_compiler

# :todo: find a way to get this from `conftest` or such
# Directory with testing modules used in some tests.
_MODULES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modules')

def test_nameclash(pyi_builder):
    # test-case for issue #964: Nameclashes in module information gathering
    # All pyinstaller specific module attributes should be prefixed,
    # to avoid nameclashes.
    pyi_builder.test_source(
        """
        import pyi_testmod_nameclash.nameclash
        """)


def test_relative_import(pyi_builder):
    pyi_builder.test_source(
        """
        import pyi_testmod_relimp.B.C
        from pyi_testmod_relimp.F import H
        import pyi_testmod_relimp.relimp1

        assert pyi_testmod_relimp.relimp1.name == 'pyi_testmod_relimp.relimp1'
        assert pyi_testmod_relimp.B.C.name == 'pyi_testmod_relimp.B.C'
        assert pyi_testmod_relimp.F.H.name == 'pyi_testmod_relimp.F.H'
        """
    )


def test_relative_import2(pyi_builder):
    pyi_builder.test_source(
        """
        import pyi_testmod_relimp2.bar
        import pyi_testmod_relimp2.bar.bar2

        pyi_testmod_relimp2.bar.say_hello_please()
        pyi_testmod_relimp2.bar.bar2.say_hello_please()
        """
    )


def test_relative_import3(pyi_builder):
    pyi_builder.test_source(
        """
        from pyi_testmod_relimp3a.aa import a1
        print(a1.getString())
        """
    )

@xfail(reason='modulegraph bug')
def test_import_missing_submodule(pyi_builder):
    # If a submodule is missing, the parent submodule must be imported.
    pyi_builder.test_source(
        """
        try:
            import pyi_testmod_missing_submod.aaa.bbb
        except ImportError as e:
            assert e.message.endswith(' bbb')
        else:
            raise RuntimeError('Buggy test-case: module'
                       'pyi_testmod_missing_submod.aaa.bbb must not exist')
        # parent module exists and must be included
        __import__('pyi_testmod_missing_submod.aaa')
        """)

def test_import_submodule_global_shadowed(pyi_builder):
    """
    Functional test validating issue #1919.

    `ModuleGraph` previously ignored `from`-style imports of submodules from
    packages whose `__init__` submodules declared global variables of the same
    name as those submodules. This test exercises this sporadic edge case by
    unsuccessfully importing a submodule "shadowed" by a global variable of the
    same name defined by their package's `__init__` submodule.
    """

    pyi_builder.test_source(
        """
        # Assert that this submodule is shadowed by a string global variable.
        from pyi_testmod_submodule_global_shadowed import submodule
        assert type(submodule) == str

        # Assert that this submodule is still frozen into this test application.
        # To do so:
        #
        # 1. Delete this global variable from its parent package.
        # 2. Assert that this submodule is unshadowed by this global variable.
        import pyi_testmod_submodule_global_shadowed, sys
        del  pyi_testmod_submodule_global_shadowed.submodule
        from pyi_testmod_submodule_global_shadowed import submodule
        assert type(submodule) == type(sys)
        """)


def test_import_submodule_global_unshadowed(pyi_builder):
    '''
    Functional test validating issue #1919.

    `ModuleGraph` previously ignored `from`-style imports of submodules from
    packages whose `__init__` submodules declared global variables of the same
    name as those submodules. This test exercises this sporadic edge case by
    successfully importing a submodule:

    * Initially "shadowed" by a global variable of the same name defined by
      their package's `__init__` submodule.
    * Subsequently "unshadowed" when this global variable is then undefined by
      their package's `__init__` submodule.
    '''

    pyi_builder.test_source(
        """
        # Assert that this submodule is unshadowed by this global variable.
        import sys
        from pyi_testmod_submodule_global_unshadowed import submodule
        assert type(submodule) == type(sys)
        """)


def test_module_with_coding_utf8(pyi_builder):
    # Module ``utf8_encoded_module`` simply has an ``coding`` header
    # and uses same German umlauts.
    pyi_builder.test_source("import module_with_coding_utf8")


def test_hiddenimport(pyi_builder):
    # The script simply does nothing, not even print out a line.
    pyi_builder.test_source('pass',
                            ['--hidden-import=a_hidden_import'])



def test_error_during_import(pyi_builder):
    # See ticket #27: historically, PyInstaller was catching all
    # errors during imports...
    pyi_builder.test_source(
        """
        try:
            import error_during_import2
        except KeyError:
            print("OK")
        else:
            raise RuntimeError("failure!")
        """)

def test_import_non_existing_raises_import_error(pyi_builder):
    pyi_builder.test_source(
        """
        try:
            import zzzzzz.zzzzzzzz.zzzzzzz.non.existing.module.error_during_import2
        except ImportError:
            print("OK")
        else:
            raise RuntimeError("ImportError not raised")
        """)

# :todo: Use some package which is already installed for some other
# reason instead of `simplejson` which is only used here.
@skipif(is_py3, reason="Python 3 doesn't use the CExtensionImporter, so it "
        "doesn't need testing.")
@importorskip('simplejson')
def test_c_extension(pyi_builder):
    pyi_builder.test_script('pyi_c_extension.py')


# Verify that __path__ is respected for imports from the filesystem:
#
# * pyi_testmod_path/
#
#   * __init__.py -- inserts a/ into __path__, then imports b, which now refers
#     to a/b.py, not ./b.py.
#   * b.py - raises an exception. **Should not be imported.**
#   * a/ -- contains no __init__.py.
#
#     * b.py - Empty. Should be imported.
@xfail(reason='__path__ not respected for filesystem modules.')
def test_import_respects_path(pyi_builder, script_dir):
    pyi_builder.test_source('import pyi_testmod_path',
      ['--additional-hooks-dir='+script_dir.join('pyi_hooks').strpath])


# Verify correct handling of sys.meta_path redirects like pkg_resources 28.6.1
# does: '_vendor.xxx' gets imported as 'extern.xxx' and using '__import__()'.
# Note: This also requires a hook, since 'pyi_testmod_metapath1._vendor' is
# not imported directly and won't be found by modulegraph.
def test_import_metapath1(pyi_builder, script_dir):
    pyi_builder.test_source('import pyi_testmod_metapath1',
      ['--additional-hooks-dir='+script_dir.join('pyi_hooks').strpath])


@importorskip('PyQt5')
def test_import_pyqt5_uic_port(script_dir, pyi_builder):
    extra_path = os.path.join(_MODULES_DIR, 'pyi_import_pyqt_uic_port')
    pyi_builder.test_script('pyi_import_pyqt5_uic_port.py',
        # Add the path to a fake PyQt5 package, used for this test.
        pyi_args=['--path', extra_path])


#--- ctypes ----

@skipif_no_compiler
@skipif(is_py35 and is_win,
        reason="MSVCR not directly loadable on py3.5, see https://bugs.python.org/issue23606")
def test_ctypes_CDLL_c(pyi_builder):
    # Make sure we are able to load the MSVCRXX.DLL resp. libc.so we are
    # currently bound. This is some of a no-brainer since the resp. dll/so
    # is collected anyway.
    pyi_builder.test_source(
        """
        import ctypes, ctypes.util
        lib = ctypes.CDLL(ctypes.util.find_library('c'))
        assert lib is not None
        """)

@skipif_no_compiler
@skipif(is_win, reason="CDLL(None) seams to be not valid on Windows")
def test_ctypes_CDLL_None(pyi_builder):
    # Make sure we are able to load CDLL(None)
    # -> pip does this for some reason
    pyi_builder.test_source(
        """
        import ctypes, ctypes.util
        lib = ctypes.CDLL(None)
        assert lib is not None
        """)

import PyInstaller.depend.utils
__orig_resolveCtypesImports = PyInstaller.depend.utils._resolveCtypesImports

def __monkeypatch_resolveCtypesImports(monkeypatch, compiled_dylib):

    def mocked_resolveCtypesImports(*args, **kwargs):
        from PyInstaller.config import CONF
        old_pathex = CONF['pathex']
        CONF['pathex'].append(str(compiled_dylib))
        res = __orig_resolveCtypesImports(*args, **kwargs)
        CONF['pathex'] = old_pathex
        return res

    # Add the path to ctypes_dylib to pathex, only for
    # _resolveCtypesImports. We can not monkeypath CONF['pathex']
    # here, as it will be overwritten when pyi_builder is starting up.
    # So be monkeypatch _resolveCtypesImports by a wrapper.
    monkeypatch.setattr(PyInstaller.depend.utils, "_resolveCtypesImports",
                        mocked_resolveCtypesImports)


#FIXME: For reusability, move this to "PyInstaller.utils.tests".
def skip_if_lib_missing(libname, text=None):
    """
    pytest decorator to evaluate the required shared lib.

    :param libname: Name of the required library.
    :param text: Text to put into the reason message
                 (defaults to 'lib%s.so' % libname)

    :return: pytest decorator with a reason.
    """
    soname = ctypes.util.find_library(libname)
    if not text:
        text = "lib%s.so" % libname
    # Return pytest decorator.
    return skipif(not (soname and ctypes.CDLL(soname)),
                  reason="required %s missing" % text)


_template_ctypes_CDLL_find_library = """
    import ctypes, ctypes.util, sys, os
    lib = ctypes.CDLL(ctypes.util.find_library(%(libname)r))
    print(lib)
    assert lib is not None and lib._name is not None
    if getattr(sys, 'frozen', False):
        soname = ctypes.util.find_library(%(libname)r)
        print(soname)
        libfile = os.path.join(sys._MEIPASS, soname)
        print(libfile)
        assert os.path.isfile(libfile), '%%s is missing' %% soname
        print('>>> file found')
    """

# Ghostscript's libgs.so should be available in may Unix/Linux systems
#
# At least on Linux, we can not use our own `ctypes_dylib` because
# `find_library` does not consult LD_LIBRARY_PATH and hence does not
# find our lib. Anyway, this test tests the path of the loaded lib and
# thus checks if libgs.so is included into the frozen exe.
# TODO: Check how this behaves on other platforms.
@skip_if_lib_missing('gs', 'libgs.so (Ghostscript)')
def test_ctypes_CDLL_find_library__gs(pyi_builder):
    libname = 'gs'
    pyi_builder.test_source(_template_ctypes_CDLL_find_library % locals())


#-- Generate test-cases for the different types of ctypes objects.

_template_ctypes_test = """
        print(lib)
        assert lib is not None and lib._name is not None
        import sys, os
        if getattr(sys, 'frozen', False):
            libfile = os.path.join(sys._MEIPASS, %(soname)r)
            print(libfile)
            assert os.path.isfile(libfile), '%(soname)s is missing'
            print('>>> file found')
    """

parameters = []
ids = []
for prefix in ('', 'ctypes.'):
    for funcname in  ('CDLL', 'PyDLL', 'WinDLL', 'OleDLL', 'cdll.LoadLibrary'):
        ids.append(prefix+funcname)
        params = (prefix+funcname, ids[-1])
        # Marking doesn't seem to chain here, so select just one skippping mark
        # instead of both.
        if not has_compiler:
            params = skipif_no_compiler(params)
        elif funcname in ("WinDLL", "OleDLL"):
            # WinDLL, OleDLL only work on windows.
            params = skipif_notwin(params)
        parameters.append(params)

@pytest.mark.parametrize("funcname,test_id", parameters, ids=ids)
def test_ctypes_gen(pyi_builder, monkeypatch, funcname, compiled_dylib, test_id):
    # evaluate the soname here, so the test-code contains a constant.
    # We want the name of the dynamically-loaded library only, not its path.
    # See discussion in https://github.com/pyinstaller/pyinstaller/pull/1478#issuecomment-139622994.
    soname = compiled_dylib.basename

    source = """
        import ctypes ; from ctypes import *
        lib = %s(%%(soname)r)
    """ % funcname + _template_ctypes_test

    __monkeypatch_resolveCtypesImports(monkeypatch, compiled_dylib.dirname)
    pyi_builder.test_source(source % locals(), test_id=test_id)


@pytest.mark.parametrize("funcname,test_id", parameters, ids=ids)
def test_ctypes_in_func_gen(pyi_builder, monkeypatch, funcname,
                            compiled_dylib, test_id):
    """
    This is much like test_ctypes_gen except that the ctypes calls
    are in a function. See issue #1620.
    """
    soname = compiled_dylib.basename

    source = ("""
    import ctypes ; from ctypes import *
    def f():
      def g():
        lib = %s(%%(soname)r)
    """ % funcname +
    _template_ctypes_test + """
      g()
    f()
    """)
    __monkeypatch_resolveCtypesImports(monkeypatch, compiled_dylib.dirname)
    pyi_builder.test_source(source % locals(), test_id=test_id)


# TODO: Add test-cases for the prefabricated library loaders supporting
# attribute accesses on windows. Example::
#
#   cdll.kernel32.GetModuleHandleA(None)
#
# Of course we need to use dlls which is not are commony available on
# windows but mot excluded in PyInstaller.depend.dylib


def test_egg_unzipped(pyi_builder):
    pathex = os.path.join(_MODULES_DIR, 'pyi_egg_unzipped.egg')
    pyi_builder.test_source(
        """
        # This code is part of the package for testing eggs in `PyInstaller`.
        import os
        import pkg_resources

        # Test ability to load resource.
        expected_data = 'This is data file for `unzipped`.'.encode('ascii')
        t = pkg_resources.resource_string('unzipped_egg', 'data/datafile.txt')
        print('Resource: %s' % t)
        t_filename = pkg_resources.resource_filename('unzipped_egg', 'data/datafile.txt')
        print('Resource filename: %s' % t_filename)
        assert t.rstrip() == expected_data

        # Test ability that module from .egg is able to load resource.
        import unzipped_egg
        assert unzipped_egg.data == expected_data

        print('Okay.')
        """,
        pyi_args=['--paths', pathex],
    )


def test_egg_zipped(pyi_builder):
    pathex = os.path.join(_MODULES_DIR, 'pyi_egg_zipped.egg')
    pyi_builder.test_source(
        """
        # This code is part of the package for testing eggs in `PyInstaller`.
        import os
        import pkg_resources

        # Test ability to load resource.
        expected_data = 'This is data file for `zipped`.'.encode('ascii')
        t = pkg_resources.resource_string('zipped_egg', 'data/datafile.txt')
        print('Resource: %s' % t)
        t_filename = pkg_resources.resource_filename('zipped_egg', 'data/datafile.txt')
        print('Resource filename: %s' % t_filename)
        assert t.rstrip() == expected_data

        # Test ability that module from .egg is able to load resource.
        import zipped_egg
        assert zipped_egg.data == expected_data

        print('Okay.')
        """,
        pyi_args=['--paths', pathex],
    )


#--- namespaces ---

def test_nspkg1(pyi_builder):
    # Test inclusion of namespace packages implemented using
    # pkg_resources.declare_namespace
    pathex = glob.glob(os.path.join(_MODULES_DIR, 'nspkg1-pkg', '*.egg'))
    pyi_builder.test_source(
        """
        import nspkg1.aaa
        import nspkg1.bbb.zzz
        import nspkg1.ccc
        """,
        pyi_args=['--paths', os.pathsep.join(pathex)],
    )


def test_nspkg1_empty(pyi_builder):
    # Test inclusion of a namespace-only packages in an zipped egg.
    # This package only defines the namespace, nothing is contained there.
    pathex = glob.glob(os.path.join(_MODULES_DIR, 'nspkg1-pkg', '*.egg'))
    pyi_builder.test_source(
        """
        import nspkg1
        print (nspkg1)
        """,
        pyi_args=['--paths', os.pathsep.join(pathex)],
    )


def test_nspkg1_bbb_zzz(pyi_builder):
    # Test inclusion of a namespace packages in an zipped egg
    pathex = glob.glob(os.path.join(_MODULES_DIR, 'nspkg1-pkg', '*.egg'))
    pyi_builder.test_source(
        """
        import nspkg1.bbb.zzz
        """,
        pyi_args=['--paths', os.pathsep.join(pathex)],
    )


def test_nspkg2(pyi_builder):
    # Test inclusion of namespace packages implemented as nspkg.pth-files
    pathex = glob.glob(os.path.join(_MODULES_DIR, 'nspkg2-pkg'))
    pyi_builder.test_source(
        """
        import nspkg2.aaa
        import nspkg2.bbb.zzz
        import nspkg2.ccc
        """,
        pyi_args=['--paths', os.pathsep.join(pathex)],
    )


@xfail(reason="modulegraph implements `pkgutil.extend_path` wrong")
def test_nspkg3(pyi_builder):
    pathex = glob.glob(os.path.join(_MODULES_DIR, 'nspkg3-pkg', '*.egg'))
    pyi_builder.test_source(
        """
        import nspkg3.aaa
        try:
            # pkgutil ignores items of sys.path that are not strings
            # referring to existing directories. So this zipped egg
            # *must* be ignored.
            import nspkg3.bbb.zzz
        except ImportError:
            pass
        else:
            raise SystemExit('nspkg3.bbb.zzz found but should not')
        try:
            import nspkg3.a
        except ImportError:
            pass
        else:
            raise SystemExit('nspkg3.a found but should not')
        import nspkg3.ccc
        """,
        pyi_args=['--paths', os.pathsep.join(pathex)],
    )

def test_nspkg3_empty(pyi_builder):
    # Test inclusion of a namespace-only package in a zipped egg
    # using pkgutil.extend_path.
    # This package only defines namespace, nothing is contained there.
    pathex = glob.glob(os.path.join(_MODULES_DIR, 'nspkg3-pkg', '*_empty.egg'))
    pyi_builder.test_source(
        """
        import nspkg3
        print (nspkg3)
        """,
        pyi_args=['--paths', os.pathsep.join(pathex)],
    )

def test_nspkg3_aaa(pyi_builder):
    # Test inclusion of a namespace package in an directory using
    # pkgutil.extend_path
    pathex = glob.glob(os.path.join(_MODULES_DIR, 'nspkg3-pkg', '*.egg'))
    pyi_builder.test_source(
        """
        import nspkg3.aaa
        """,
        pyi_args=['--paths', os.pathsep.join(pathex)],
    )

def test_nspkg3_bbb_zzz(pyi_builder):
    # Test inclusion of a namespace package in an zipped egg using
    # pkgutil.extend_path
    pathex = glob.glob(os.path.join(_MODULES_DIR, 'nspkg3-pkg', '*.egg'))
    pyi_builder.test_source(
        """
        import nspkg3.bbb.zzz
        """,
        pyi_args=['--paths', os.pathsep.join(pathex)],
    )

@skipif(is_py2, reason="requires Python 3")
def test_nspkg_pep420(pyi_builder):
    # Test inclusion of PEP 420 namespace packages.
    pathex = glob.glob(os.path.join(_MODULES_DIR, 'nspkg-pep420', 'path*'))
    pyi_builder.test_source(
        """
        import package.sub1
        import package.sub2
        import package.subpackage.sub
        import package.nspkg.mod
        """,
        pyi_args=['--paths', os.pathsep.join(pathex)],
    )


#--- hooks related stuff ---

def test_pkg_without_hook_for_pkg(pyi_builder, script_dir):
    # The package `pkg_without_hook_for_pkg` does not have a hook, but
    # `pkg_without_hook_for_pkg.sub1` has one. And this hook includes
    # the "hidden" import `pkg_without_hook_for_pkg.sub1.sub11`
    pyi_builder.test_source(
        'import pkg_without_hook_for_pkg.sub1',
        ['--additional-hooks-dir=%s' % script_dir.join('pyi_hooks')])


@xfail(is_darwin, reason='Issue #1895.')
def test_app_with_plugin(pyi_builder, data_dir, monkeypatch):
    datas = os.pathsep.join(('data/*/static_plugin.py', os.curdir))
    pyi_builder.test_script('pyi_app_with_plugin.py',
                            pyi_args=['--add-data', datas])
