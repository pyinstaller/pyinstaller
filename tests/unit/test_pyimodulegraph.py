#-----------------------------------------------------------------------------
# Copyright (c) 2005-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------


import types
import pytest
import itertools

from PyInstaller import HOMEPATH
from PyInstaller.depend import analysis
from PyInstaller.lib.modulegraph import modulegraph
import PyInstaller.log as logging
from PyInstaller.utils.tests import gen_sourcefile


def test_get_co_using_ctypes(tmpdir):
    logging.logger.setLevel(logging.DEBUG)
    mg = analysis.PyiModuleGraph(HOMEPATH, excludes=["xencodings"])
    script = tmpdir.join('script.py')
    script.write('import ctypes')
    script_filename = str(script)
    mg.run_script(script_filename)
    res = mg.get_co_using_ctypes()
    # Script's code object must be in the results
    assert script_filename in res
    assert isinstance(res[script_filename], types.CodeType), res


def test_get_co_using_ctypes_from_extension():
    # If an extension module has an hidden import to ctypes (e.g. added by the
    # hook), the extension module must not show up in the result of
    # `get_co_using_ctypes()`, since it has no code-object to be analyzed.
    # See issue #2492 and test_regression::issue_2492.
    logging.logger.setLevel(logging.DEBUG)
    mg = analysis.PyiModuleGraph(HOMEPATH, excludes=["xencodings"])
    struct = mg.createNode(modulegraph.Extension, '_struct', 'struct.so')
    mg.implyNodeReference(struct, 'ctypes') # simulate the hidden import
    res = mg.get_co_using_ctypes()
    # _struct must not be in the results
    assert '_struct' not in res


class FakePyiModuleGraph(analysis.PyiModuleGraph):
    def _analyze_base_modules(self):
        # suppress this to speed up set-up
        self._base_modules = ()


@pytest.fixture
def fresh_pyi_modgraph(monkeypatch):
    """
    Get a fresh PyiModuleGraph
    """

    def fake_base_modules(self):
        # speed up set up
        self._base_modules = ()

    logging.logger.setLevel(logging.DEBUG)
    # ensure we get a fresh PyiModuleGraph
    monkeypatch.setattr(analysis, "_cached_module_graph_", None)
    # speed up setup
    monkeypatch.setattr(analysis.PyiModuleGraph,
                        "_analyze_base_modules", fake_base_modules)
    return analysis.initialize_modgraph()


def test_cached_graph_is_not_leaking(fresh_pyi_modgraph, monkeypatch, tmpdir):
    """
    Ensure cached PyiModulegraph can separate imports between scripts.
    """
    mg = fresh_pyi_modgraph
    # self-test 1: uuid is not included in the graph by default
    src = gen_sourcefile(tmpdir, """print""", test_id="1")
    mg.run_script(str(src))
    assert not mg.findNode("uuid")  # self-test

    # self-test 2: uuid is available and included when imported
    src = gen_sourcefile(tmpdir, """import uuid""", test_id="2")
    node = mg.run_script(str(src))
    assert node is not None
    names = [n.identifier for n in mg.flatten(start=node)]
    assert "uuid" in names

    # the acutal test: uuid is not leaking to the other script
    src = gen_sourcefile(tmpdir, """print""", test_id="3")
    node = mg.run_script(str(src))
    assert node is not None
    names = [n.identifier for n in mg.flatten(start=node)]
    assert "uuid" not in names


def test_cached_graph_is_not_leaking_hidden_imports(fresh_pyi_modgraph, tmpdir):
    """
    Ensure cached PyiModulegraph can separate hidden imports between scripts.
    """
    mg = fresh_pyi_modgraph
    # self-test 1: skipped here, see test_cached_graph_is_not_leaking

    # self-test 2: uuid is included when hidden imported
    src = gen_sourcefile(tmpdir, """print""", test_id="2")
    node = mg.run_script(str(src))
    assert node is not None
    mg.add_hiddenimports(["uuid"])
    names = [n.identifier for n in mg.flatten(start=node)]
    assert "uuid" in names

    # the acutal test: uuid is not leaking to the other script
    src = gen_sourcefile(tmpdir, """print""", test_id="3")
    node = mg.run_script(str(src))
    assert node is not None
    names = [n.identifier for n in mg.flatten(start=node)]
    assert "uuid" not in names


def test_graph_collects_script_dependencies(fresh_pyi_modgraph, tmpdir):
    mg = fresh_pyi_modgraph
    # self-test 1: uuid is not included in the graph by default
    src1 = gen_sourcefile(tmpdir, """print""", test_id="1")
    node = mg.run_script(str(src1))
    assert node is not None
    assert not mg.findNode("uuid")  # self-test

    # Add script importing uuid
    src2 = gen_sourcefile(tmpdir, """import uuid""", test_id="2")
    mg.run_script(str(src2))
    assert mg.findNode("uuid")  # self-test

    # The acutal test: uuid is (indirectly) linked to the first script
    names = [n.identifier for n in mg.flatten(start=node)]
    assert str(src2) in names
    assert "uuid" in names


def _gen_pseudo_rthooks(name, rthook_dat, tmpdir, gen_files=True):
    hd = tmpdir.ensure(name, dir=True)
    if gen_files:
        for fn in itertools.chain(*rthook_dat.values()):
            hd.ensure("rthooks", fn)
    rhd = hd.ensure("rthooks.dat")
    rhd.write(repr(rthook_dat))
    return hd


def test_collect_rthooks_1(tmpdir, monkeypatch):
    rh1 = {"test_pyimodulegraph_mymod1": ["m1.py"]}
    hd1 = _gen_pseudo_rthooks("h1", rh1, tmpdir)
    mg = FakePyiModuleGraph(HOMEPATH, user_hook_dirs=[str(hd1)])
    assert len(mg._available_rthooks["test_pyimodulegraph_mymod1"]) == 1


def test_collect_rthooks_2(tmpdir, monkeypatch):
    rh1 = {"test_pyimodulegraph_mymod1": ["m1.py"]}
    rh2 = {"test_pyimodulegraph_mymod2": ["rth1.py", "rth1.py"]}
    hd1 = _gen_pseudo_rthooks("h1", rh1, tmpdir)
    hd2 = _gen_pseudo_rthooks("h2", rh2, tmpdir)
    mg = FakePyiModuleGraph(HOMEPATH, user_hook_dirs=[str(hd1), str(hd2)])
    assert len(mg._available_rthooks["test_pyimodulegraph_mymod1"]) == 1
    assert len(mg._available_rthooks["test_pyimodulegraph_mymod2"]) == 2


def test_collect_rthooks_3(tmpdir, monkeypatch):
    rh1 = {"test_pyimodulegraph_mymod1": ["m1.py"]}
    rh2 = {"test_pyimodulegraph_mymod1": ["rth1.py", "rth1.py"]}
    hd1 = _gen_pseudo_rthooks("h1", rh1, tmpdir)
    hd2 = _gen_pseudo_rthooks("h2", rh2, tmpdir)
    mg = FakePyiModuleGraph(HOMEPATH, user_hook_dirs=[str(hd1), str(hd2)])
    assert len(mg._available_rthooks["test_pyimodulegraph_mymod1"]) == 1


def test_collect_rthooks_fail_1(tmpdir, monkeypatch):
    rh1 = {"test_pyimodulegraph_mymod1": ["m1.py"]}
    hd1 = _gen_pseudo_rthooks("h1", rh1, tmpdir, False)
    with pytest.raises(AssertionError):
        FakePyiModuleGraph(HOMEPATH, user_hook_dirs=[str(hd1)])
