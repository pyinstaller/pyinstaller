#-----------------------------------------------------------------------------
# Copyright (c) 2005-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import pytest
import types

from PyInstaller import HOMEPATH
from PyInstaller.depend import analysis
from PyInstaller.lib.modulegraph import modulegraph


def test_get_co_using_ctypes(tmpdir):
    script = tmpdir.join('script.py')
    script.write('import ctypes')
    mg = analysis.PyiModuleGraph(HOMEPATH)
    mg.run_script(str(script))
    res = mg.get_co_using_ctypes()
    assert len(res) == 1
    assert isinstance(res[str(script)], types.CodeType)


def test_get_co_using_ctypes_from_extension():
    # If an extension module has an hidden import to ctypes (e.g. added by the
    # hook), the extension moduel must nor show up in the result of
    # get_co_using_ctypes(). See issue #2492 and test_regression::issue_2492.
    mg = analysis.PyiModuleGraph(HOMEPATH)
    struct = mg.createNode(modulegraph.Extension, '_struct', 'struct.so')
    mg.implyNodeReference(struct, 'ctypes') # simulate the hidden import
    res = mg.get_co_using_ctypes()
    assert len(res) == 0
