#-----------------------------------------------------------------------------
# Copyright (c) 2005-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import itertools
import textwrap
import types

import pytest

from PyInstaller import HOMEPATH
from PyInstaller.depend import analysis
from PyInstaller.lib.modulegraph import modulegraph
import PyInstaller.log as logging
from PyInstaller.utils.tests import gen_sourcefile


def test_get_co_using_ctypes(tmp_path):
    logging.logger.setLevel(logging.DEBUG)
    mg = analysis.PyiModuleGraph(HOMEPATH, excludes=["xencodings"])
    script = tmp_path / 'script.py'
    script.write_text("import ctypes", encoding='utf-8')
    script_filename = str(script)
    mg.add_script(script_filename)
    res = mg.get_code_using("ctypes")
    # Script's code object must be in the results
    assert script_filename in res
    assert isinstance(res[script_filename], types.CodeType), res


def test_get_co_using_ctypes_from_extension():
    # If an extension module has an hidden import to ctypes (e.g. added by the hook), the extension module must not
    # show up in the result of `get_co_using_ctypes()`, since it has no code-object to be analyzed.
    # See issue #2492 and test_regression::issue_2492.
    logging.logger.setLevel(logging.DEBUG)
    mg = analysis.PyiModuleGraph(HOMEPATH, excludes=["xencodings"])
    struct = mg.createNode(modulegraph.Extension, '_struct', 'struct.so')
    mg.implyNodeReference(struct, 'ctypes')  # simulate the hidden import
    res = mg.get_code_using("ctypes")
    # _struct must not be in the results
    assert '_struct' not in res


def test_metadata_collection(tmp_path):
    from PyInstaller.utils.hooks import copy_metadata

    mg = analysis.PyiModuleGraph(HOMEPATH, excludes=["xencodings"])

    source = textwrap.dedent(
        '''
        from importlib.metadata import distribution, version
        import importlib.metadata

        distribution("setuptools")
        importlib.metadata.version("altgraph")
        '''
    )
    script = tmp_path / 'script.py'
    script.write_text(source, encoding='utf-8')

    mg.add_script(str(script))
    metadata = mg.metadata_required()

    assert copy_metadata("setuptools")[0] in metadata
    assert copy_metadata("altgraph")[0] in metadata


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
    monkeypatch.setattr(analysis.PyiModuleGraph, "_analyze_base_modules", fake_base_modules)
    return analysis.initialize_modgraph()


def test_cached_graph_is_not_leaking(fresh_pyi_modgraph, monkeypatch, tmp_path):
    """
    Ensure cached PyiModulegraph can separate imports between scripts.
    """
    mg = fresh_pyi_modgraph
    # self-test 1: uuid is not included in the graph by default
    src = gen_sourcefile(tmp_path, """print""", test_id="1")
    mg.add_script(str(src))
    assert not mg.find_node("uuid")  # self-test

    # self-test 2: uuid is available and included when imported
    src = gen_sourcefile(tmp_path, """import uuid""", test_id="2")
    node = mg.add_script(str(src))
    assert node is not None
    names = [n.identifier for n in mg.iter_graph(start=node)]
    assert "uuid" in names

    # the actual test: uuid is not leaking to the other script
    src = gen_sourcefile(tmp_path, """print""", test_id="3")
    node = mg.add_script(str(src))
    assert node is not None
    names = [n.identifier for n in mg.iter_graph(start=node)]
    assert "uuid" not in names


def test_cached_graph_is_not_leaking_hidden_imports(fresh_pyi_modgraph, tmp_path):
    """
    Ensure cached PyiModulegraph can separate hidden imports between scripts.
    """
    mg = fresh_pyi_modgraph
    # self-test 1: skipped here, see test_cached_graph_is_not_leaking

    # self-test 2: uuid is included when hidden imported
    src = gen_sourcefile(tmp_path, """print""", test_id="2")
    node = mg.add_script(str(src))
    assert node is not None
    mg.add_hiddenimports(["uuid"])
    names = [n.identifier for n in mg.iter_graph(start=node)]
    assert "uuid" in names

    # the actual test: uuid is not leaking to the other script
    src = gen_sourcefile(tmp_path, """print""", test_id="3")
    node = mg.add_script(str(src))
    assert node is not None
    names = [n.identifier for n in mg.iter_graph(start=node)]
    assert "uuid" not in names


def test_graph_collects_script_dependencies(fresh_pyi_modgraph, tmp_path):
    mg = fresh_pyi_modgraph
    # self-test 1: uuid is not included in the graph by default
    src1 = gen_sourcefile(tmp_path, """print""", test_id="1")
    node = mg.add_script(str(src1))
    assert node is not None
    assert not mg.find_node("uuid")  # self-test

    # Add script importing uuid
    src2 = gen_sourcefile(tmp_path, """import uuid""", test_id="2")
    mg.add_script(str(src2))
    assert mg.find_node("uuid")  # self-test

    # The actual test: uuid is (indirectly) linked to the first script
    names = [n.identifier for n in mg.iter_graph(start=node)]
    assert str(src2) in names
    assert "uuid" in names


def _gen_pseudo_rthooks(name, rthook_dat, tmp_path, gen_files=True):
    # Create hooks directory
    hooks_dir = tmp_path / name
    rthooks_dir = hooks_dir / 'rthooks'
    rthooks_dir.mkdir(parents=True)

    # Create hook files
    if gen_files:
        for hook_file in itertools.chain(*rthook_dat.values()):
            (rthooks_dir / hook_file).touch()  # Create empty hook file

    # Create rthooks.dat file
    (hooks_dir / 'rthooks.dat').write_text(repr(rthook_dat), encoding='utf-8')
    return hooks_dir


def test_collect_rthooks_1(tmp_path, monkeypatch):
    rh1 = {"test_pyimodulegraph_mymod1": ["m1.py"]}
    hd1 = _gen_pseudo_rthooks("h1", rh1, tmp_path)
    mg = FakePyiModuleGraph(
        HOMEPATH,
        user_hook_dirs=[
            (str(hd1), analysis.HOOK_PRIORITY_BUILTIN_HOOKS),
        ],
    )
    assert len(mg._available_rthooks["test_pyimodulegraph_mymod1"]) == 1


def test_collect_rthooks_2(tmp_path, monkeypatch):
    rh1 = {"test_pyimodulegraph_mymod1": ["m1.py"]}
    rh2 = {"test_pyimodulegraph_mymod2": ["rth1.py", "rth1.py"]}
    hd1 = _gen_pseudo_rthooks("h1", rh1, tmp_path)
    hd2 = _gen_pseudo_rthooks("h2", rh2, tmp_path)
    mg = FakePyiModuleGraph(
        HOMEPATH,
        user_hook_dirs=[
            (str(hd1), analysis.HOOK_PRIORITY_BUILTIN_HOOKS),
            (str(hd2), analysis.HOOK_PRIORITY_BUILTIN_HOOKS),
        ],
    )
    assert len(mg._available_rthooks["test_pyimodulegraph_mymod1"]) == 1
    assert len(mg._available_rthooks["test_pyimodulegraph_mymod2"]) == 2


def test_collect_rthooks_3(tmp_path, monkeypatch):
    rh1 = {"test_pyimodulegraph_mymod1": ["m1.py"]}
    rh2 = {"test_pyimodulegraph_mymod1": ["rth1.py", "rth1.py"]}
    hd1 = _gen_pseudo_rthooks("h1", rh1, tmp_path)
    hd2 = _gen_pseudo_rthooks("h2", rh2, tmp_path)
    mg = FakePyiModuleGraph(
        HOMEPATH,
        user_hook_dirs=[
            (str(hd1), analysis.HOOK_PRIORITY_BUILTIN_HOOKS),
            (str(hd2), analysis.HOOK_PRIORITY_BUILTIN_HOOKS),
        ],
    )
    assert len(mg._available_rthooks["test_pyimodulegraph_mymod1"]) == 1


def test_collect_rthooks_fail_1(tmp_path, monkeypatch):
    rh1 = {"test_pyimodulegraph_mymod1": ["m1.py"]}
    hd1 = _gen_pseudo_rthooks("h1", rh1, tmp_path, False)
    with pytest.raises(AssertionError):
        FakePyiModuleGraph(
            HOMEPATH,
            user_hook_dirs=[
                (str(hd1), analysis.HOOK_PRIORITY_BUILTIN_HOOKS),
            ],
        )


class FakeGraph(analysis.PyiModuleGraph):
    """
    A simplified module graph containing a single node module *foo* with user-defined content.
    """
    def __init__(self, source):
        self.code = compile(source, "<>", "exec")

    def get_code_using(self, package):
        return {"foo": self.code}


def test_metadata_searching():
    """
    Test the top level for bytecode scanning for metadata requirements.
    """
    from PyInstaller.utils.hooks import copy_metadata

    # This test analyses code which implies that PyInstaller's own metadata (and possibly that of its dependencies) is
    # required.
    pyinstaller = set(copy_metadata("pyinstaller"))
    with_dependencies = set(copy_metadata("pyinstaller", recursive=True))

    self = FakeGraph("from importlib.metadata import distribution; distribution('pyinstaller')")
    assert pyinstaller == self.metadata_required()

    self = FakeGraph("import pkg_resources; pkg_resources.get_distribution('pyinstaller')")
    assert pyinstaller == self.metadata_required()

    self = FakeGraph("import pkg_resources; pkg_resources.require('pyinstaller')")
    assert with_dependencies == self.metadata_required()
