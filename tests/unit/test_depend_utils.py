#-----------------------------------------------------------------------------
# Copyright (c) 2005-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import os
import pytest
import textwrap

from PyInstaller.depend import utils
from PyInstaller.compat import (is_unix, PYDYLIB_NAMES)


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


@pytest.mark.skipif(not is_unix, reason="requires a Unix System")
def test_ldconfig_cache():
    utils.load_ldconfig_cache()
    libpath = None
    for soname in utils.LDCONFIG_CACHE:
        if soname.startswith('libc.so.'):
            libpath = utils.LDCONFIG_CACHE[soname]
            break
    assert libpath, 'libc.so not found'
    assert os.path.isfile(libpath)
