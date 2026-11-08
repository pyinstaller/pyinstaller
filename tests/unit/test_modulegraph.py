#-----------------------------------------------------------------------------
# Copyright (c) 2005-2026, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""
Tests for the rewritten :mod:`PyInstaller.depend.modulegraph` package.

These tests are ported from the former ``test_pyimodulegraph.py`` (which
exercised the old ``PyiModuleGraph`` wrapper around the vendored
``PyInstaller.lib.modulegraph``); the class names and entry points have been
updated to the new, single :class:`ModuleGraph` API:

* The old ``analysis.PyiModuleGraph(...)`` constructor is now simply
  ``ModuleGraph(pyi_homepath=...)`` -- the PyInstaller-specific hook
  machinery is built in and activated by passing ``pyi_homepath``.
* The old ``createNode()`` / ``implyNodeReference()`` pair is replaced by
  ``ModuleGraph._add_node()`` (the graph's single node-insertion point) and
  ``ModuleGraph.add_edge()``.
* The old ``analysis.initialize_modgraph()`` entry point moved to
  ``PyInstaller.depend.modulegraph.graph.initialize_modgraph``.
"""

import importlib.machinery
import itertools
import os
import py_compile
import sys
import textwrap
import types
import zipfile

import pytest

from PyInstaller import HOMEPATH
from PyInstaller.depend.modulegraph import ModuleGraph, ModuleType
from PyInstaller.depend.modulegraph import graph as graph_module
from PyInstaller.depend.modulegraph.graph import initialize_modgraph
from PyInstaller.depend.imphook import HOOK_PRIORITY_BUILTIN_HOOKS
import PyInstaller.log as logging
from PyInstaller.utils.tests import gen_sourcefile


def test_get_code_using_ctypes(tmp_path):
    """A script that imports ctypes must appear in get_code_using()."""
    logging.logger.setLevel(logging.DEBUG)
    mg = ModuleGraph(pyi_homepath=HOMEPATH, excludes=("xencodings",))
    script = tmp_path / 'script.py'
    script.write_text("import ctypes", encoding='utf-8')
    script_filename = str(script)
    mg.add_script(script_filename)
    res = mg.get_code_using("ctypes")
    # Script's code object must be in the results
    assert script_filename in res
    assert isinstance(res[script_filename], types.CodeType), res


def test_get_code_using_ctypes_from_extension():
    """
    If an extension module has an hidden import to ctypes (e.g. added by the hook), the extension module must not
    show up in the result of `get_code_using()`, since it has no code-object to be analyzed.
    See issue #2492 and test_regression::issue_2492.
    """
    logging.logger.setLevel(logging.DEBUG)
    mg = ModuleGraph(pyi_homepath=HOMEPATH, excludes=("xencodings",))
    # Simulate an extension module with no code object, linked by an
    # implied ("hidden") import edge to ctypes. The old API did this with
    # createNode(..., Extension) + implyNodeReference(); the new graph's
    # single node-insertion point is _add_node() and edges are recorded
    # with add_edge().
    struct = mg._add_node('_struct', ModuleType.EXTENSION, path='struct.so')
    mg.add_edge(struct, 'ctypes')  # simulate the hidden import
    res = mg.get_code_using("ctypes")
    # _struct must not be in the results
    assert '_struct' not in res


def test_metadata_collection(tmp_path):
    from PyInstaller.utils.hooks import copy_metadata

    mg = ModuleGraph(pyi_homepath=HOMEPATH, excludes=("xencodings",))

    source = textwrap.dedent(
        '''
        from importlib.metadata import distribution, version
        import importlib.metadata
        importlib.metadata.distribution("setuptools")
        importlib.metadata.version("altgraph")
        '''
    )
    script = tmp_path / 'script.py'
    script.write_text(source, encoding='utf-8')

    mg.add_script(str(script))
    metadata = mg.metadata_required()

    assert copy_metadata("setuptools")[0] in metadata
    assert copy_metadata("altgraph")[0] in metadata


class _SuppressBaseModules(ModuleGraph):
    """
    A ModuleGraph that skips the (slow) base-library analysis so tests
    construct graphs almost instantly; the same trick the old
    ``FakePyiModuleGraph`` used on ``_analyze_base_modules``.
    """

    def _analyze_base_modules(self):
        # suppress this to speed up set-up
        self._base_modules = ()


@pytest.fixture
def fresh_modgraph(monkeypatch):
    """
    Get a fresh ModuleGraph (cache reset, base-module analysis suppressed).
    """
    def fake_base_modules(self):
        # speed up setup
        self._base_modules = ()

    logging.logger.setLevel(logging.DEBUG)
    # ensure we get a fresh ModuleGraph: reset the module-level cache in
    # graph.py so initialize_modgraph() builds (and re-caches) from scratch.
    monkeypatch.setattr(graph_module, "_cached_module_graph_", None)
    # speed up setup
    monkeypatch.setattr(ModuleGraph, "_analyze_base_modules", fake_base_modules)
    return initialize_modgraph()


def test_cached_graph_is_not_leaking(fresh_modgraph, tmp_path):
    """
    Ensure the cached ModuleGraph can separate imports between scripts.
    """
    mg = fresh_modgraph
    # self-test 1: uuid is not included in the graph by default
    src = gen_sourcefile(tmp_path, """print""", test_id="1")
    mg.add_script(str(src))
    assert not mg.find_node("uuid")  # self-test

    # self-test 2: uuid is available and included when imported
    src = gen_sourcefile(tmp_path, """import uuid""", test_id="2")
    node = mg.add_script(str(src))
    assert node is not None
    names = [n.ident for n in mg.iter_graph(start=node)]
    assert "uuid" in names

    # the actual test: uuid is not leaking to the other script
    src = gen_sourcefile(tmp_path, """print""", test_id="3")
    node = mg.add_script(str(src))
    assert node is not None
    names = [n.ident for n in mg.iter_graph(start=node)]
    assert "uuid" not in names


def test_cached_graph_is_not_leaking_hidden_imports(fresh_modgraph, tmp_path):
    """
    Ensure the cached ModuleGraph can separate hidden imports between scripts.
    """
    mg = fresh_modgraph
    # self-test 1: skipped here, see test_cached_graph_is_not_leaking

    # self-test 2: uuid is included when hidden imported
    src = gen_sourcefile(tmp_path, """print""", test_id="2")
    node = mg.add_script(str(src))
    assert node is not None
    mg.add_hiddenimports(["uuid"])
    names = [n.ident for n in mg.iter_graph(start=node)]
    assert "uuid" in names

    # the actual test: uuid is not leaking to the other script
    src = gen_sourcefile(tmp_path, """print""", test_id="3")
    node = mg.add_script(str(src))
    assert node is not None
    names = [n.ident for n in mg.iter_graph(start=node)]
    assert "uuid" not in names


def test_graph_collects_script_dependencies(fresh_modgraph, tmp_path):
    mg = fresh_modgraph
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
    names = [n.ident for n in mg.iter_graph(start=node)]
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


def test_collect_rthooks_1(tmp_path):
    rh1 = {"test_modulegraph_mymod1": ["m1.py"]}
    hd1 = _gen_pseudo_rthooks("h1", rh1, tmp_path)
    mg = _SuppressBaseModules(
        pyi_homepath=HOMEPATH,
        user_hook_dirs=((str(hd1), HOOK_PRIORITY_BUILTIN_HOOKS),),
    )
    assert len(mg._available_rthooks["test_modulegraph_mymod1"]) == 1


def test_collect_rthooks_2(tmp_path):
    rh1 = {"test_modulegraph_mymod1": ["m1.py"]}
    rh2 = {"test_modulegraph_mymod2": ["rth1.py", "rth1.py"]}
    hd1 = _gen_pseudo_rthooks("h1", rh1, tmp_path)
    hd2 = _gen_pseudo_rthooks("h2", rh2, tmp_path)
    mg = _SuppressBaseModules(
        pyi_homepath=HOMEPATH,
        user_hook_dirs=(
            (str(hd1), HOOK_PRIORITY_BUILTIN_HOOKS),
            (str(hd2), HOOK_PRIORITY_BUILTIN_HOOKS),
        ),
    )
    assert len(mg._available_rthooks["test_modulegraph_mymod1"]) == 1
    assert len(mg._available_rthooks["test_modulegraph_mymod2"]) == 2


def test_collect_rthooks_3(tmp_path):
    rh1 = {"test_modulegraph_mymod1": ["m1.py"]}
    rh2 = {"test_modulegraph_mymod1": ["rth1.py", "rth1.py"]}
    hd1 = _gen_pseudo_rthooks("h1", rh1, tmp_path)
    hd2 = _gen_pseudo_rthooks("h2", rh2, tmp_path)
    mg = _SuppressBaseModules(
        pyi_homepath=HOMEPATH,
        user_hook_dirs=(
            (str(hd1), HOOK_PRIORITY_BUILTIN_HOOKS),
            (str(hd2), HOOK_PRIORITY_BUILTIN_HOOKS),
        ),
    )
    assert len(mg._available_rthooks["test_modulegraph_mymod1"]) == 1


def test_collect_rthooks_fail_1(tmp_path):
    rh1 = {"test_modulegraph_mymod1": ["m1.py"]}
    hd1 = _gen_pseudo_rthooks("h1", rh1, tmp_path, False)
    with pytest.raises(AssertionError):
        _SuppressBaseModules(
            pyi_homepath=HOMEPATH,
            user_hook_dirs=((str(hd1), HOOK_PRIORITY_BUILTIN_HOOKS),),
        )


class _FakeGraph(ModuleGraph):
    """
    A simplified module graph containing a single node module *foo* with
    user-defined content. Only ``get_code_using()`` is faked; the rest of
    the (slow) hook machinery is never touched because no real analysis is
    run in the tests that use this class.
    """

    def __init__(self, source):
        self.code = compile(source, "<>", "exec")

    def get_code_using(self, package):
        return {"foo": self.code}


def test_metadata_searching():
    """
    Test the top level for bytecode scanning for metadata requirements.
    """
    from importlib.metadata import PackageNotFoundError
    import pytest

    from PyInstaller.utils.hooks import copy_metadata

    # This test analyses code which implies that PyInstaller's own metadata (and possibly that of its dependencies) is
    # required. When running from a source tree without an installed distribution (no dist-info), this metadata is
    # unavailable and the test cannot run.
    try:
        pyinstaller = set(copy_metadata("pyinstaller"))
        with_dependencies = set(copy_metadata("pyinstaller", recursive=True))
    except PackageNotFoundError:
        pytest.skip("PyInstaller distribution metadata is not available (package not installed)")

    self = _FakeGraph("from importlib.metadata import distribution; distribution('pyinstaller')")
    assert pyinstaller == self.metadata_required()

    self = _FakeGraph("import pkg_resources; pkg_resources.get_distribution('pyinstaller')")
    assert pyinstaller == self.metadata_required()

    self = _FakeGraph("import pkg_resources; pkg_resources.require('pyinstaller')")
    assert with_dependencies == self.metadata_required()


# ---------------------------------------------------------------------------
# Ported from the old vendored-lib suite (tests/unit/test_modulegraph/)
# ---------------------------------------------------------------------------

def test_implies(tmp_path):
    """
    ``implies={...}`` must add hidden dependencies to the graph.

    Ported from the old suite's ``test_implies.py`` (which exercised
    ``modulegraph.ModuleGraph(implies={...})`` against the vendored lib);
    rewritten for the new API, where ``dependencies()`` returns the nodes a
    node imports and ``dependents()`` the nodes importing it.
    """
    root = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'test_modulegraph_data', 'testpkg-relimport')

    # First check that 'getopt' isn't accidentally in the graph:
    mg = ModuleGraph(path=[root] + sys.path)
    mg.add_script(os.path.join(root, 'script.py'))
    node = mg.find_node('mod')
    assert node is not None
    assert node.module_type == ModuleType.PURE

    assert mg.find_node('getopt') is None

    # Now check that adding an implied dependency actually adds 'getopt'
    # to the graph:
    mg = ModuleGraph(path=[root] + sys.path, implies={'mod': ['getopt']})
    mg.add_script(os.path.join(root, 'script.py'))
    node = mg.find_node('mod')
    assert node is not None
    assert node.module_type == ModuleType.PURE

    getopt_node = mg.find_node('getopt')
    assert getopt_node is not None
    assert getopt_node.module_type == ModuleType.PURE

    # Check that the edges are correct:
    assert getopt_node in mg.dependencies(node)
    assert node in mg.dependents(getopt_node)


def test_implies_packaged(tmp_path):
    """
    Like :func:`test_implies`, but the implied dependency hangs off a module
    inside a package (``pkg.relative`` instead of ``mod``).
    """
    root = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'test_modulegraph_data', 'testpkg-relimport')

    mg = ModuleGraph(path=[root] + sys.path)
    mg.add_script(os.path.join(root, 'script.py'))
    assert mg.find_node('getopt') is None

    mg = ModuleGraph(path=[root] + sys.path, implies={'pkg.relative': ['getopt']})
    mg.add_script(os.path.join(root, 'script.py'))

    pkg_node = mg.find_node('pkg.relative')
    assert pkg_node is not None
    assert pkg_node.module_type == ModuleType.PURE

    getopt_node = mg.find_node('getopt')
    assert getopt_node is not None
    assert getopt_node.module_type == ModuleType.PURE

    assert getopt_node in mg.dependencies(pkg_node)
    assert pkg_node in mg.dependents(getopt_node)


def test_pep420_namespace_packages():
    """
    PEP 420 namespace packages must resolve across multiple ``path`` entries.

    Ported from the old suite's ``test_pep420_nspkg.py`` (upstream issue
    #4425: pkgutil-style and PEP 420 namespace package handling), rewritten
    for the new API where node kinds are :class:`ModuleType` members instead
    of distinct node classes.
    """
    src = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'test_modulegraph_data', 'testpkg-pep420-namespace')
    path1 = os.path.join(src, 'path1')
    path2 = os.path.join(src, 'path2')

    mf = ModuleGraph(path=[path1, path2] + sys.path)

    # The root 'package' exists as a namespace package in both path1 and
    # path2 -- it must be classified as a namespace package.
    mf.import_hook('package')
    node = mf.find_node('package')
    assert node is not None
    assert node.module_type == ModuleType.NAMESPACE
    assert node.ident == 'package'

    # Submodules of the namespace package must be found via its full
    # multi-path __path__.
    mf.import_hook('package.sub1')
    node = mf.find_node('package.sub1')
    assert node is not None
    assert node.module_type == ModuleType.PURE
    assert node.ident == 'package.sub1'

    mf.import_hook('package.sub2')
    node = mf.find_node('package.sub2')
    assert node is not None
    assert node.module_type == ModuleType.PURE

    # A regular sub-package inside the namespace package.
    mf.import_hook('package.subpackage.sub')
    node = mf.find_node('package.subpackage.sub')
    assert node is not None
    assert node.module_type == ModuleType.PURE

    # ...and the root must still be the namespace package.
    node = mf.find_node('package')
    assert node.module_type == ModuleType.NAMESPACE

    # A regular package living on the namespace-package path.
    mf.import_hook('package.nspkg.mod')
    node = mf.find_node('package.nspkg.mod')
    assert node is not None
    assert node.module_type == ModuleType.PURE


def test_deep_import_chain_no_recursion(tmp_path):
    """
    Regression test for the old, recursive modulegraph's ``RecursionError``
    on deep import chains (upstream issues #2875, #2911, #3040, #3752 and
    friends).

    The new engine is iterative (work-queue driven, see ``QueueItem``), so a
    chain several times deeper than Python's recursion limit must be
    processed without any error at all.
    """
    depth = 4 * sys.getrecursionlimit()
    pkg = tmp_path / "deep"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")

    # deep.m0 imports deep.m1 imports ... imports deep.m(depth-1)
    for i in range(depth):
        body = f"import deep.m{i + 1}\n" if i + 1 < depth else ""
        (pkg / f"m{i}.py").write_text(body, encoding="utf-8")

    script = tmp_path / "script.py"
    script.write_text("import deep.m0\n", encoding="utf-8")

    mg = ModuleGraph(path=[str(tmp_path)] + sys.path)
    # Must not raise RecursionError:
    mg.add_script(str(script))

    # Every module in the chain must have entered the graph.
    for i in range(depth):
        node = mg.find_node(f"deep.m{i}")
        assert node is not None, f"deep.m{i} missing from graph"
        assert node.module_type == ModuleType.PURE


# ---------------------------------------------------------------------------
# Ported from the old standalone suite (tests/unit/test_modulegraph_more.py)
# ---------------------------------------------------------------------------


def _import_and_get_node(tmp_path, module_name, path=None):
    """
    Analyze a throwaway script that imports *module_name* and return the
    module's node.

    The old ``test_modulegraph_more.py`` suite built its test data on the
    fly instead of shipping it as fixtures; this helper preserves that
    pattern.
    """
    script = tmp_path / 'script.py'
    script.write_text(f"import {module_name}", encoding='utf-8')
    if path is None:
        path = [str(tmp_path)]
    mg = ModuleGraph(path=path)
    mg.add_script(str(script))
    return mg.find_node(module_name)


def test_sourcefile(tmp_path):
    (tmp_path / 'source.py').write_text("###", encoding='utf-8')
    node = _import_and_get_node(tmp_path, 'source')
    assert node.module_type == ModuleType.PURE


def test_invalid_sourcefile(tmp_path):
    # The old graph recorded unparseable source as an ``InvalidSourceModule``
    # node; the new engine simply drops the module instead (see
    # ``ModuleGraph._create_node``).
    (tmp_path / 'invalid_source.py').write_text("invalid python-source code", encoding='utf-8')
    node = _import_and_get_node(tmp_path, 'invalid_source')
    assert node is None


def test_invalid_compiledfile(tmp_path):
    # The old graph recorded corrupt bytecode as an ``InvalidCompiledModule``
    # node; the new engine simply drops the module instead.
    (tmp_path / 'invalid_compiled.pyc').write_text("invalid byte-code", encoding='utf-8')
    node = _import_and_get_node(tmp_path, 'invalid_compiled')
    assert node is None


def test_builtin(tmp_path):
    node = _import_and_get_node(tmp_path, 'sys', path=sys.path)
    assert node.module_type == ModuleType.BUILTIN


def test_extension(tmp_path):
    node = _import_and_get_node(tmp_path, '_ctypes', path=sys.path)
    assert node.module_type == ModuleType.EXTENSION


def test_package(tmp_path):
    # Create package; stuff/__init__.py
    (tmp_path / 'stuff').mkdir()
    pysrc = tmp_path / 'stuff' / '__init__.py'
    pysrc.write_text("###", encoding='utf-8')
    # Analyze
    node = _import_and_get_node(tmp_path, 'stuff')
    assert node.module_type == ModuleType.PACKAGE
    # Source is always preferred over any stale .pyc sibling.
    assert node.path == str(pysrc)
    assert list(node.spec.submodule_search_locations) == [str(pysrc.parent)]


@pytest.mark.parametrize(
    "num, modname, is_package",
    (
        # package's __init__ module is an extension
        (1, "myextpkg", True),
        # __init__.py beside the __init__ module being an extension
        (2, "myextpkg", True),
        # Importing a module beside
        (3, "myextpkg.other", False),
        # sub-package's __init__ module is an extension
        (4, "myextpkg.subpkg", True),
        # importing a module beside, but from a sub-package
        (5, "myextpkg.subpkg.other", False),
    )
)
def test_package_init_is_extension(tmp_path, num, modname, is_package):
    # Regression: Recursion too deep
    EXTENSION_SUFFIX = importlib.machinery.EXTENSION_SUFFIXES[0]

    def _write_module(*args):
        module_file = tmp_path.joinpath(*args)
        module_file.parent.mkdir(parents=True, exist_ok=True)
        module_file.write_text('###', encoding='utf-8')
        return module_file

    def create_package_files(test_case):
        m = _write_module('myextpkg', '__init__' + EXTENSION_SUFFIX)
        if test_case == 1:
            return m
        _write_module('myextpkg', '__init__.py')
        if test_case == 2:
            return m  # return extension module anyway
        m = _write_module('myextpkg', 'other.py')
        m = _write_module('myextpkg', 'other' + EXTENSION_SUFFIX)
        if test_case == 3:
            return m
        m = _write_module('myextpkg', 'subpkg', '__init__.py')
        m = _write_module('myextpkg', 'subpkg', '__init__' + EXTENSION_SUFFIX)
        if test_case == 4:
            return m
        m = _write_module('myextpkg', 'subpkg', 'other.py')
        m = _write_module('myextpkg', 'subpkg', 'other' + EXTENSION_SUFFIX)
        return m

    module_file = create_package_files(num)
    node = _import_and_get_node(tmp_path, modname)
    # The old graph had a distinct ``ExtensionPackage`` node class; the new
    # engine classifies an extension ``__init__`` as a plain extension node,
    # keeping the package's search locations on the spec.
    assert node.module_type == ModuleType.EXTENSION
    if is_package:
        assert list(node.spec.submodule_search_locations) == [str(module_file.parent)]
    else:
        assert node.spec.submodule_search_locations is None
    assert node.path == str(module_file)


def test_relative_import_missing(tmp_path):
    libdir = tmp_path / 'lib'

    pkg = libdir / 'pkg'
    (pkg / 'x' / 'y').mkdir(parents=True)  # Create the whole package directory tree
    (pkg / '__init__.py').write_text("#", encoding='utf-8')
    (pkg / 'x' / '__init__.py').write_text("#", encoding='utf-8')
    (pkg / 'x' / 'y' / '__init__.py').write_text("#", encoding='utf-8')
    (pkg / 'x' / 'y' / 'z.py').write_text("from . import DoesNotExist", encoding='utf-8')

    script = tmp_path / 'script.py'
    script.write_text("import pkg.x.y.z", encoding='utf-8')

    mg = ModuleGraph(path=[str(libdir)])
    mg.add_script(str(script))
    assert mg.find_node('pkg.x.y.z').module_type == ModuleType.PURE
    assert mg.find_node('pkg.x.y.DoesNotExist').module_type == ModuleType.MISSING


# -- Tests with a single module in a zip-file --


def test_zipped_module_source(tmp_path):
    pysrc = tmp_path / 'stuff.py'
    pysrc.write_text("###", encoding='utf-8')

    zipfilename = tmp_path / 'unstuff.zip'
    with zipfile.ZipFile(zipfilename, mode='w') as zfh:
        zfh.write(pysrc, 'stuff.py')

    node = _import_and_get_node(tmp_path, 'stuff', path=[str(zipfilename)])
    assert node.module_type == ModuleType.PURE
    assert node.path.startswith(os.path.join(str(zipfilename), 'stuff.py'))


def test_zipped_module_source_and_compiled(tmp_path):
    pysrc = tmp_path / 'stuff.py'
    pysrc.write_text("###", encoding='utf-8')

    pyc = pysrc.with_suffix('.pyc')
    py_compile.compile(pysrc, pyc)

    zipfilename = tmp_path / 'unstuff.zip'
    with zipfile.ZipFile(zipfilename, mode='w') as zfh:
        zfh.write(pysrc, 'stuff.py')
        zfh.write(pyc, 'stuff.pyc')

    node = _import_and_get_node(tmp_path, 'stuff', path=[str(zipfilename)])
    # Do not care whether it is source or compiled, as long as it is neither invalid nor missing.
    assert node.module_type in (ModuleType.PURE, ModuleType.BYTECODE)
    assert node.path.startswith(os.path.join(str(zipfilename), 'stuff.py'))


# -- Tests with a package in a zip-file --


def test_zipped_package_source(tmp_path):
    pkg = tmp_path / 'stuff'
    pkg.mkdir()

    pysrc = pkg / '__init__.py'
    pysrc.write_text('###', encoding='utf-8')

    zipfilename = tmp_path / 'stuff.zip'
    with zipfile.ZipFile(zipfilename, mode='w') as zfh:
        zfh.write(pkg, 'stuff')
        zfh.write(pysrc, 'stuff/__init__.py')

    node = _import_and_get_node(tmp_path, 'stuff', path=[str(zipfilename)])
    assert node.module_type == ModuleType.PACKAGE
    assert list(node.spec.submodule_search_locations) == [os.path.join(str(zipfilename), 'stuff')]


def test_zipped_package_source_and_compiled(tmp_path):
    pkg = tmp_path / 'stuff'
    pkg.mkdir()

    pysrc = pkg / '__init__.py'
    pysrc.write_text('###', encoding='utf-8')

    pyc = pysrc.with_suffix('.pyc')
    py_compile.compile(pysrc, pyc)

    zipfilename = tmp_path / 'stuff.zip'
    with zipfile.ZipFile(zipfilename, mode='w') as zfh:
        zfh.write(pkg, 'stuff')
        zfh.write(pysrc, 'stuff/__init__.py')
        zfh.write(pyc, 'stuff/__init__.pyc')

    node = _import_and_get_node(tmp_path, 'stuff', path=[str(zipfilename)])
    # zipimporter may point the spec at either archive entry; both must keep
    # the package's search locations intact.
    assert node.module_type == ModuleType.PACKAGE
    assert list(node.spec.submodule_search_locations) == [os.path.join(str(zipfilename), 'stuff')]


# -- Symlinks (POSIX only; Windows development machines cannot create them) --


@pytest.mark.darwin
@pytest.mark.linux
def test_symlinks(tmp_path):
    (tmp_path / 'p1').mkdir()
    p1_init = tmp_path / 'p1' / '__init__.py'
    p1_init.write_text("###", encoding='utf-8')

    (tmp_path / 'p2').mkdir()
    p2_init = tmp_path / 'p2' / '__init__.py'
    p2_init.write_text("###", encoding='utf-8')

    base_dir = tmp_path / 'base'
    (base_dir / 'p1').mkdir(parents=True)

    os.symlink(str(p1_init), str(base_dir / 'p1' / '__init__.py'))
    os.symlink(str(p2_init), str(base_dir / 'p1' / 'p2.py'))

    node = _import_and_get_node(base_dir, 'p1.p2')
    assert node.module_type == ModuleType.PURE


# -- Bytecode scanning --

# The old suite scanned code through both an AST and a bytecode path; the
# new engine is bytecode-only, so both old assertions collapse into the
# single ``_scan_code`` API below.


def _scan_code_imports_and_names(code):
    """
    Split the graph scanner's yields into ``(imports, defined names)``.
    """
    imports = []
    names = set()
    for data in ModuleGraph._scan_code(compile(textwrap.dedent(code), 'dummy', 'exec')):
        if isinstance(data, set):
            names = data
        else:
            imports.append(data)
    return imports, names


def test_scan_code__empty():
    imports, names = _scan_code_imports_and_names("# empty code")
    assert imports == []
    assert names == set()


def test_scan_code__basic():
    imports, names = _scan_code_imports_and_names(
        """
        import os.path
        from sys import maxint, exitfunc, platform
        del exitfunc
        def testfunc():
            import shutil
        """
    )
    assert imports == [
        ('os.path', 0, ()),
        ('sys', 0, ('maxint', 'exitfunc', 'platform')),
        ('shutil', 0, ()),
    ]
    # ``import os.path`` binds only 'os'; the from-import binds its fromlist;
    # 'del exitfunc' removes that binding again; the nested 'import shutil'
    # is function-local and must not leak into the module's namespace.
    assert names == {'os', 'maxint', 'platform', 'testfunc'}


# -- SWIG packages --

# NOTE: the old suite also carried a set of SWIG-workaround tests
# (``test_swig_import_simple*``, ``test_swig_import_from_top_level*``),
# exercising the wrapper-module rewriting that lived in the old
# ``modulegraph._safe_import_hook``. The new engine does not reimplement
# that machinery (yet); those tests remain in git history until the
# feature returns. The tests below cover the SWIG-adjacent behavior that
# must hold regardless: plain (non-SWIG) candidate modules resolve like
# any other module.


def test_swig_top_level_but_no_swig_at_all(tmp_path):
    # From the script import an absolute module which looks like a SWIG candidate but is no SWIG module.
    # See issue #3040 ('_decimal').
    # The center of this test-case is that it does not raise a recursion too deep error.
    libdir = tmp_path / 'lib'
    libdir.mkdir()
    (libdir / 'pyi_dezimal.py').write_text("import _pyi_dezimal", encoding='utf-8')

    script = tmp_path / 'script.py'
    script.write_text("import pyi_dezimal", encoding='utf-8')

    mg = ModuleGraph(path=[str(libdir)])
    mg.add_script(str(script))

    assert mg.find_node('pyi_dezimal').module_type == ModuleType.PURE
    assert mg.find_node('_pyi_dezimal').module_type == ModuleType.MISSING


def test_swig_top_level_but_no_swig_at_all_existing(tmp_path):
    # Like test_swig_top_level_but_no_swig_at_all, but the "C" module exists.
    # The test-case is here for symmetry.
    libdir = tmp_path / 'lib'
    libdir.mkdir()
    (libdir / 'pyi_dezimal.py').write_text("import _pyi_dezimal", encoding='utf-8')
    (libdir / '_pyi_dezimal.py').write_text("#", encoding='utf-8')

    script = tmp_path / 'script.py'
    script.write_text("import pyi_dezimal", encoding='utf-8')

    mg = ModuleGraph(path=[str(libdir)])
    mg.add_script(str(script))

    assert mg.find_node('pyi_dezimal').module_type == ModuleType.PURE
    assert mg.find_node('_pyi_dezimal').module_type == ModuleType.PURE


def test_swig_candidate_but_not_swig(tmp_path):
    # From a package module import an absolute module which looks like a SWIG candidate, but is no SWIG module.
    # See issue #2911 (tifffile).
    # The center of this test-case is that it does not raise a recursion too deep error.
    libdir = tmp_path / 'lib'

    pkg = libdir / 'pkg'
    pkg.mkdir(parents=True)
    (pkg / '__init__.py').write_text("from . import mymod", encoding='utf-8')
    (pkg / 'mymod.py').write_text("import _mymod", encoding='utf-8')
    (pkg / '_mymod.py').write_text("#", encoding='utf-8')

    script = tmp_path / 'script.py'
    script.write_text("from pkg import XXX", encoding='utf-8')

    mg = ModuleGraph(path=[str(libdir)])
    mg.add_script(str(script))

    assert mg.find_node('pkg').module_type == ModuleType.PACKAGE
    assert mg.find_node('pkg.mymod').module_type == ModuleType.PURE
    assert mg.find_node('pkg._mymod') is None
    # This is not a SWIG module, thus the SWIG import mechanism should not trigger.
    assert mg.find_node('_mymod').module_type == ModuleType.MISSING


def test_swig_candidate_but_not_swig2(tmp_path):
    """
    Variation of test_swig_candidate_but_not_swig using different import statements
    (like tifffile/tifffile.py does).
    """
    libdir = tmp_path / 'lib'

    pkg = libdir / 'pkg'
    pkg.mkdir(parents=True)
    (pkg / '__init__.py').write_text("from . import mymod", encoding='utf-8')
    (pkg / '_mymod.py').write_text("#", encoding='utf-8')
    (pkg / 'mymod.py').write_text(
        "\n".join(["from . import _mymod", "import _mymod"]),
        encoding='utf-8',
    )

    script = tmp_path / 'script.py'
    script.write_text("from pkg import XXX", encoding='utf-8')

    mg = ModuleGraph(path=[str(libdir)])
    mg.add_script(str(script))

    assert mg.find_node('pkg').module_type == ModuleType.PACKAGE
    assert mg.find_node('pkg.mymod').module_type == ModuleType.PURE
    assert mg.find_node('pkg._mymod').module_type == ModuleType.PURE
    assert mg.find_node('_mymod').module_type == ModuleType.MISSING


def test_swig_candidate_but_not_swig_missing(tmp_path):
    # Like test_swig_candidate_but_not_swig, but the "C" module is missing and should be reported as a MissingModule.
    libdir = tmp_path / 'lib'

    pkg = libdir / 'pkg'
    pkg.mkdir(parents=True)
    (pkg / '__init__.py').write_text("from . import mymod", encoding='utf-8')
    (pkg / 'mymod.py').write_text("import _mymod", encoding='utf-8')

    script = tmp_path / 'script.py'
    script.write_text("import pkg", encoding='utf-8')

    mg = ModuleGraph(path=[str(libdir)])
    mg.add_script(str(script))

    assert mg.find_node('pkg').module_type == ModuleType.PACKAGE
    assert mg.find_node('pkg.mymod').module_type == ModuleType.PURE
    assert mg.find_node('pkg._mymod') is None
    assert mg.find_node('_mymod').module_type == ModuleType.MISSING


def test_swig_candidate_but_not_swig_missing2(tmp_path):
    """
    Variation of test_swig_candidate_but_not_swig_missing using different import statements
    (like tifffile/tifffile.py does).
    """
    libdir = tmp_path / 'lib'

    pkg = libdir / 'pkg'
    pkg.mkdir(parents=True)
    (pkg / '__init__.py').write_text("from . import mymod", encoding='utf-8')
    (pkg / 'mymod.py').write_text(
        "\n".join(["from . import _mymod", "import _mymod"]),
        encoding='utf-8',
    )

    script = tmp_path / 'script.py'
    script.write_text("import pkg", encoding='utf-8')

    mg = ModuleGraph(path=[str(libdir)])
    mg.add_script(str(script))

    assert mg.find_node('pkg').module_type == ModuleType.PACKAGE
    assert mg.find_node('pkg.mymod').module_type == ModuleType.PURE
    assert mg.find_node('pkg._mymod').module_type == ModuleType.MISSING
    assert mg.find_node('_mymod').module_type == ModuleType.MISSING
