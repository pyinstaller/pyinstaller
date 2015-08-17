#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from __future__ import unicode_literals

import os
import pytest
import ctypes, ctypes.util

from PyInstaller.compat import is_win
from PyInstaller.utils.tests import skipif, importorskip, xfail_py2


# Directory with data for some tests.
_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')



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

_template_ctypes_CDLL_const = """
    import ctypes, ctypes.util, sys, os
    lib = ctypes.CDLL(%(soname)r)
    print(lib)
    assert lib is not None and lib._name is not None
    if getattr(sys, 'frozen', False):
        libfile = os.path.join(sys._MEIPASS, %(soname)r)
        print(libfile)
        assert os.path.isfile(libfile), '%(soname)s is missing'
        print('>>> file found')
    """

# Ghostscript's libgs.so should be available in may Unix/Linux systems
@pytest.mark.xfail(reason='fetching dll-name from ctypes.util.find_library() is unsupported')
@skip_if_lib_missing('gs', 'libgs.so (Ghostscript)')
def test_ctypes_CDLL_find_library__gs(pyi_builder):
    libname = 'gs'
    pyi_builder.test_source(_template_ctypes_CDLL_find_library % locals())


@skip_if_lib_missing('gs', 'libgs.so (Ghostscript)')
def test_ctypes_CDLL__gs(pyi_builder):
    # evaluate the soname here, so the test-code contains a constant
    soname = ctypes.util.find_library('gs')
    pyi_builder.test_source(_template_ctypes_CDLL_const % locals())


@pytest.mark.xfail(reason='fetching dll-name from ctypes.util.find_library() is unsupported')
@skip_if_lib_missing('usb-1.0')
def test_ctypes_CDLL_find_library__usb(pyi_builder):
    libname = 'usb-1.0'
    pyi_builder.test_source(_template_ctypes_CDLL_find_library % locals())


@skip_if_lib_missing('usb-1.0')
def test_ctypes_CDLL__usb(pyi_builder):
    # evaluate the soname here, so the test-code contains a constant
    soname = ctypes.util.find_library('usb-1.0')
    pyi_builder.test_source(_template_ctypes_CDLL_const % locals())
