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


def test_relative_import(pyi_builder):
    pyi_builder.test_script('pyi_import_relative.py')


def test_relative_import2(pyi_builder):
    pyi_builder.test_script('pyi_import_relative2.py')


def test_relative_import3(pyi_builder):
    pyi_builder.test_script('pyi_import_relative3.py')


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
@skip_if_lib_missing('gs', 'libgs.so (Ghostscript)')
def test_ctypes_CDLL_find_library__gs(pyi_builder):
    libname = 'gs'
    pyi_builder.test_source(_template_ctypes_CDLL_find_library % locals())


#-- Generate test-cases for the different types of ctypes objects.

libname = 'gs'
reason = 'libgs.so (Ghostscript)'
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
def test_ctypes_gen(pyi_builder, funcname, compiled_dylib, test_id):
    # Workaround, see above.
    # :todo: remove this workaround (see above)
    if not is_win and funcname.endswith(("WinDLL", "OleDLL")):
        pytest.skip('%s requires windows' % funcname)
    # Add the path to ctypes_dylib to the OS path.
    old_path = os.environ['PATH']
    try:
        os.environ['PATH'] += os.pathsep + compiled_dylib.strpath
        # evaluate the soname here, so the test-code contains a constant
        soname = ctypes.util.find_library('ctypes_dylib')
    finally:
        os.environ['PATH'] = old_path
    soname = str(compiled_dylib.join('ctypes_dylib.so'))
    assert soname
    print(soname)
    source = """
        import ctypes ; from ctypes import *
        lib = %s(%%(soname)r)
    """ % funcname + _template_ctypes_test
    source = source +_template_ctypes_test
    pyi_builder.test_source(source % locals(), test_id=test_id)

# TODO: Add test-cases forthe prefabricated library loaders supporting
# attribute accesses on windows. Example::
#
#   cdll.kernel32.GetModuleHandleA(None)
#
# Of course we need to use dlls which is not are commony available on
# windows but mot excluded in PyInstaller.depend.dylib


@skip_if_lib_missing('usb-1.0')
def test_ctypes_CDLL_find_library__usb(pyi_builder):
    libname = 'usb-1.0'
    pyi_builder.test_source(_template_ctypes_CDLL_find_library % locals())


@skip_if_lib_missing('usb-1.0')
def test_ctypes_CDLL__usb(pyi_builder):
    # evaluate the soname here, so the test-code contains a constant
    soname = ctypes.util.find_library('usb-1.0')
    script = """
        import ctypes
        lib = ctypes.CDLL(%(soname)r)
    """ + _template_ctypes_test
    pyi_builder.test_source(script % locals())
