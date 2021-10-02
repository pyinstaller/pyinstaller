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

import os
import pytest
import textwrap

from PyInstaller.depend import utils
from PyInstaller.compat import is_win, is_musl, is_macos_11_compat

CTYPES_CLASSNAMES = (
    'CDLL', 'ctypes.CDLL',
    'WinDLL', 'ctypes.WinDLL',
    'OleDLL', 'ctypes.OleDLL',
    'PyDLL', 'ctypes.PyDLL',
)  # yapf: disable


def __scan_code_for_ctypes(code, monkeypatch, extended_args):
    # _resolveCtypesImports would filter our some of our names
    monkeypatch.setattr(utils, '_resolveCtypesImports', lambda cbinaries: cbinaries)
    code = textwrap.dedent(code)

    if extended_args:
        # Chuck in a load of preceding rubbish to test if the bytecode scanner can correctly
        # handle the EXTENDED_ARGS opcode.
        from test_bytecode import many_constants, many_globals
        code = many_constants() + many_globals() + code

    co = compile(code, 'dummy', 'exec')
    #import pdb ; pdb.set_trace()
    return utils.scan_code_for_ctypes(co)


@pytest.mark.parametrize('classname', CTYPES_CLASSNAMES)
@pytest.mark.parametrize('extended_args', [False, True])
def test_ctypes_CDLL_call(monkeypatch, classname, extended_args):
    code = "%s('somelib.xxx')" % classname
    res = __scan_code_for_ctypes(code, monkeypatch, extended_args)
    assert res == set(['somelib.xxx'])


@pytest.mark.parametrize('classname', CTYPES_CLASSNAMES)
@pytest.mark.parametrize('extended_args', [False, True])
def test_ctypes_LibraryLoader(monkeypatch, classname, extended_args):
    # This type of usage is only valif on Windows and the lib-name will always get `.dll` appended.
    code = "%s.somelib" % classname.lower()
    res = __scan_code_for_ctypes(code, monkeypatch, extended_args)
    assert res == set(['somelib.dll'])


@pytest.mark.parametrize('classname', CTYPES_CLASSNAMES)
@pytest.mark.parametrize('extended_args', [False, True])
def test_ctypes_LibraryLoader_LoadLibrary(monkeypatch, classname, extended_args):
    code = "%s.LoadLibrary('somelib.xxx')" % classname.lower()
    res = __scan_code_for_ctypes(code, monkeypatch, extended_args)
    assert res == set(['somelib.xxx'])


@pytest.mark.parametrize('extended_args', [False, True])
@pytest.mark.skipif(is_musl, reason="find_library() doesn't work on musl")
@pytest.mark.skipif(is_macos_11_compat, reason="find_library() requires python built with Big Sur support.")
def test_ctypes_util_find_library(monkeypatch, extended_args):
    # for lind_library() we need a lib actually existing on the system
    if is_win:
        libname = "KERNEL32"
    else:
        libname = "c"
    code = "ctypes.util.find_library('%s')" % libname
    res = __scan_code_for_ctypes(code, monkeypatch, extended_args)
    assert res


def test_ctypes_util_find_library_as_default_argument():
    # Test-case for fix:
    # commit 55b542f135340c612a861cfcce0f86c4e5a968df
    # Author: Hartmut Goebel <h.goebel@crazy-compilers.com>
    # Date:   Thu Nov 19 14:45:30 2015 +0100
    code = """
    def locate_library(loader=ctypes.util.find_library):
        pass
    """
    code = textwrap.dedent(code)
    co = compile(code, '<ctypes_util_find_library_as_default_argument>', 'exec')
    utils.scan_code_for_ctypes(co)


@pytest.mark.linux
def test_ldconfig_cache():
    utils.load_ldconfig_cache()

    if is_musl:
        # load_ldconfig_cache() should be a no-op on musl because musl does not use ldconfig.
        assert not utils.LDCONFIG_CACHE
        return

    libpath = None
    for soname in utils.LDCONFIG_CACHE:
        if soname.startswith('libc.so.'):
            libpath = utils.LDCONFIG_CACHE[soname]
            break
    assert libpath, 'libc.so not found'
    assert os.path.isfile(libpath)
