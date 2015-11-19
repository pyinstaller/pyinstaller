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
import textwrap

from PyInstaller.depend import utils


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
