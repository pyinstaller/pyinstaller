# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import os
import pytest
import ctypes, ctypes.util

from PyInstaller.compat import is_win
from PyInstaller.utils.tests import skipif, importorskip, xfail_py2, skipif_notwin

# :todo: find a way to get this from `conftest` or such
# Directory with testing modules used in some tests.
_MODULES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modules')

def test_relative_import(pyi_builder):
    pyi_builder.test_script('pyi_import_relative.py')


def test_relative_import2(pyi_builder):
    pyi_builder.test_script('pyi_import_relative2.py')


def test_relative_import3(pyi_builder):
    pyi_builder.test_script('pyi_import_relative3.py')

def test_import_pyqt5_uic_port(pyi_builder):
    extra_path = os.path.join(_MODULES_DIR, 'pyi_import_pyqt.uic.port')
    pyi_builder.test_script('pyi_import_pyqt5.uic.port.py',
                            pyi_args=['--path', extra_path], )


#--- ctypes ----

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

parameters = []
ids = []
for prefix in ('', 'ctypes.'):
    for funcname in  ('CDLL', 'PyDLL', 'WinDLL', 'OleDLL', 'cdll.LoadLibrary'):
        ids.append(prefix+funcname)
        params = (prefix+funcname, ids[-1])
        # Workaround a problem in pytest: skipif on a parameter will
        # completely replace the skipif on the test function. See
        # https://github.com/pytest-dev/pytest/issues/954
        # :todo: reanable this when pytest supports this
        #if funcname in ("WinDLL", "OleDLL"):
        #    # WinDLL, OleDLL only work on windows.
        #    params = skipif_notwin(params)
        parameters.append(params)

@pytest.mark.parametrize("funcname,test_id", parameters, ids=ids)
def test_ctypes_gen(pyi_builder, monkeypatch, funcname, compiled_dylib, test_id):
    # Workaround, see above.
    # :todo: remove this workaround (see above)
    if not is_win and funcname.endswith(("WinDLL", "OleDLL")):
        pytest.skip('%s requires windows' % funcname)

    # evaluate the soname here, so the test-code contains a constant.
    # We want the name of the dynamically-loaded library only, not its path.
    # See discussion in https://github.com/pyinstaller/pyinstaller/pull/1478#issuecomment-139622994.
    soname = compiled_dylib.basename

    source = """
        import ctypes ; from ctypes import *
        lib = %s(%%(soname)r)
    """ % funcname + _template_ctypes_test
    source = source +_template_ctypes_test

    __monkeypatch_resolveCtypesImports(monkeypatch, compiled_dylib.dirname)
    pyi_builder.test_source(source % locals(), test_id=test_id)


# TODO: Add test-cases for the prefabricated library loaders supporting
# attribute accesses on windows. Example::
#
#   cdll.kernel32.GetModuleHandleA(None)
#
# Of course we need to use dlls which is not are commony available on
# windows but mot excluded in PyInstaller.depend.dylib
