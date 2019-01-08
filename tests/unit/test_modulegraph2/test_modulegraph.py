import unittest
import pathlib
import contextlib
import sys
import os
import importlib

from modulegraph2 import (
    ModuleGraph,
    Script,
    SourceModule,
    MissingModule,
    BuiltinModule,
    Package,
    DependencyInfo,
)

INPUT_DIR = pathlib.Path(__file__).resolve().parent / "modulegraph-dir"


class TestModuleGraphScripts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for mod in sys.modules:
            if not hasattr(sys.modules[mod], "__file__"):
                continue
            if sys.modules[mod].__file__ is None:
                continue

    @classmethod
    def tearDownClass(cls):
        to_remove = []
        for mod in sys.modules:
            if (
                hasattr(sys.modules[mod], "__file__")
                and sys.modules[mod].__file__ is not None
                and sys.modules[mod].__file__.startswith(os.fspath(INPUT_DIR))
            ):
                to_remove.append(mod)
        for mod in to_remove:
            del sys.modules[mod]

        importlib.invalidate_caches()

    def assertValidScriptNode(self, node, script_file):
        self.assertIsInstance(node, Script)
        self.assertEqual(node.name, str(script_file))
        self.assertEqual(node.filename, script_file)
        self.assertIs(node.distribution, None)
        self.assertIs(node.loader, None)
        self.assertEqual(node.extension_attributes, {})

    def test_trivial_script(self):
        mg = ModuleGraph()
        mg.add_script(INPUT_DIR / "trivial-script")

        self.assertEqual(len(list(mg.roots())), 1)
        node, = mg.roots()

        self.assertValidScriptNode(node, INPUT_DIR / "trivial-script")

        self.assertEqual(len(list(mg.iter_graph(node=node))), 1)
        graph_node, = mg.iter_graph(node=node)
        self.assertIs(graph_node, node)

    def no_test_stdlib_script(self):
        mg = ModuleGraph()
        mg.add_script(INPUT_DIR / "stdlib-script")

        self.assertEqual(len(list(mg.roots())), 1)
        node, = mg.roots()

        self.assertValidScriptNode(node, INPUT_DIR / "stdlib-script")

        node = mg.find_node("os")
        self.assertIsInstance(node, SourceModule)

        node = mg.find_node("xml.etree.ElementTree")
        self.assertIsInstance(node, SourceModule)

        mg.report()


class TestModuleGraphAbsoluteImports(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, os.fspath(INPUT_DIR))

    def tearDown(self):
        assert sys.path[0] == os.fspath(INPUT_DIR)
        del sys.path[0]

    def assert_has_node(self, mg, node_name, node_class=None):
        n = mg.find_node(node_name)
        if n is None:
            self.fail(f"Cannot find {node_name!r} in graph")

        elif node_class is not None and not isinstance(n, node_class):
            self.fail(
                f"Node for {node_name!r} is not an instance of {node_class.__name__} but {type(n).__name__}"
            )

    def assert_has_edge(self, mg, from_name, to_name, edge_data):
        self.assert_has_node(mg, from_name)
        self.assert_has_node(mg, to_name)

        try:
            edge = mg.edge_data(from_name, to_name)

        except KeyError:
            pass
        else:
            self.assertEqual(edge, edge_data)
            return

        self.fail(f"No edge between {from_name!r} and {to_name!r}")

    def assert_has_roots(self, mg, *node_names):
        roots = set(node_names)
        self.assertEqual({n.identifier for n in mg.roots()}, roots)

    def assert_has_nodes(self, mg, *node_names):
        nodes = set(node_names)
        self.assertEqual({n.identifier for n in mg.iter_graph()}, nodes)

    def assert_edge_count(self, mg, edge_count):
        self.assertEqual(len(list(mg.edges())), edge_count)

    def test_no_imports(self):
        mg = ModuleGraph()
        mg.add_module("no_imports")

        self.assert_has_node(mg, "no_imports", SourceModule)

        self.assert_edge_count(mg, 0)

        self.assert_has_roots(mg, "no_imports")
        self.assert_has_nodes(mg, "no_imports")

    def test_global_import(self):
        mg = ModuleGraph()
        mg.add_module("global_import")

        self.assert_has_node(mg, "global_import", SourceModule)
        self.assert_has_node(mg, "no_imports", SourceModule)
        self.assert_has_edge(
            mg, "global_import", "no_imports", DependencyInfo(False, False)
        )

        self.assert_edge_count(mg, 1)

        self.assert_has_roots(mg, "global_import")
        self.assert_has_nodes(mg, "global_import", "no_imports")

        # XXX: Validate edge data

    def test_circular_imports(self):
        mg = ModuleGraph()
        mg.add_module("circular_a")

        self.assert_has_node(mg, "circular_a", SourceModule)
        self.assert_has_node(mg, "circular_b", SourceModule)
        self.assert_has_node(mg, "circular_c", SourceModule)

        self.assert_has_edge(
            mg, "circular_a", "circular_b", DependencyInfo(False, False)
        )
        self.assert_has_edge(
            mg, "circular_b", "circular_c", DependencyInfo(False, False)
        )
        self.assert_has_edge(
            mg, "circular_c", "circular_a", DependencyInfo(False, False)
        )

        self.assert_edge_count(mg, 3)

        self.assert_has_roots(mg, "circular_a")
        self.assert_has_nodes(mg, "circular_a", "circular_b", "circular_c")

    def test_missing_toplevel(self):
        mg = ModuleGraph()
        mg.add_module("missing")

        self.assert_has_node(mg, "missing", SourceModule)
        self.assert_has_node(mg, "nosuchmodule", MissingModule)

        self.assert_has_edge(
            mg, "missing", "nosuchmodule", DependencyInfo(False, False)
        )
        self.assert_edge_count(mg, 1)

        self.assert_has_roots(mg, "missing")
        self.assert_has_nodes(mg, "missing", "nosuchmodule")

    def test_missing_in_package(self):
        mg = ModuleGraph()
        mg.add_module("missing_in_package")

        self.assert_has_node(mg, "missing_in_package", SourceModule)
        self.assert_has_node(mg, "package", Package)
        self.assert_has_node(mg, "package.missingmodule", MissingModule)

        self.assert_has_edge(
            mg,
            "missing_in_package",
            "package.missingmodule",
            DependencyInfo(False, False),
        )
        self.assert_has_edge(mg, "package.missingmodule", "package", None)
        self.assert_edge_count(mg, 2)

        self.assert_has_roots(mg, "missing_in_package")
        self.assert_has_nodes(
            mg, "missing_in_package", "package", "package.missingmodule"
        )

    def test_missing_package(self):
        mg = ModuleGraph()
        mg.add_module("missing_package")

        self.assert_has_node(mg, "missing_package", SourceModule)
        self.assert_has_node(mg, "missingpackage", MissingModule)
        self.assert_has_node(mg, "missingpackage.module", MissingModule)

        self.assert_has_edge(
            mg, "missing_package", "missingpackage.module", DependencyInfo(False, False)
        )
        self.assert_has_edge(mg, "missingpackage.module", "missingpackage", None)
        self.assert_edge_count(mg, 2)

        self.assert_has_roots(mg, "missing_package")
        self.assert_has_nodes(
            mg, "missing_package", "missingpackage", "missingpackage.module"
        )

    def test_package_import_one_level(self):
        mg = ModuleGraph()
        mg.add_module("package_import_single_level")

        self.assert_has_node(mg, "package_import_single_level")
        self.assert_has_node(mg, "package.submod")
        self.assert_has_node(mg, "package")
        self.assert_has_node(mg, "no_imports")

        self.assert_has_edge(
            mg,
            "package_import_single_level",
            "package.submod",
            DependencyInfo(False, False),
        )
        self.assert_has_edge(mg, "package.submod", "package", None)
        self.assert_has_edge(
            mg, "package.submod", "no_imports", DependencyInfo(False, False)
        )
        self.assert_edge_count(mg, 3)

        self.assert_has_roots(mg, "package_import_single_level")
        self.assert_has_nodes(
            mg, "package_import_single_level", "package", "package.submod", "no_imports"
        )

    def test_package_import_two_levels(self):
        mg = ModuleGraph()
        mg.add_module("package_import_two_levels")

        self.assert_has_node(mg, "package_import_two_levels")
        self.assert_has_node(mg, "package.submod2")
        self.assert_has_node(mg, "package")
        self.assert_has_node(mg, "no_imports")
        self.assert_has_node(mg, "global_import")

        self.assert_has_edge(
            mg,
            "package_import_two_levels",
            "package.submod2",
            DependencyInfo(False, False),
        )
        self.assert_has_edge(mg, "package.submod2", "package", None)
        self.assert_has_edge(
            mg, "package.submod2", "global_import", DependencyInfo(False, False)
        )
        self.assert_has_edge(
            mg, "global_import", "no_imports", DependencyInfo(False, False)
        )
        self.assert_edge_count(mg, 4)

        self.assert_has_roots(mg, "package_import_two_levels")
        self.assert_has_nodes(
            mg,
            "package_import_two_levels",
            "package",
            "package.submod2",
            "no_imports",
            "global_import",
        )

    def test_import_two_levels(self):
        mg = ModuleGraph()
        mg.add_module("import_two_levels")

        self.assert_has_node(mg, "import_two_levels")
        self.assert_has_node(mg, "package")
        self.assert_has_node(mg, "package.subpackage")
        self.assert_has_node(mg, "package.subpackage.subpackage2")
        self.assert_has_node(mg, "package.subpackage.subpackage2.subsubmod")
        self.assert_has_node(mg, "package.subpackage.submod")

        self.assert_has_edge(
            mg,
            "import_two_levels",
            "package.subpackage.subpackage2.subsubmod",
            DependencyInfo(False, False),
        )
        self.assert_has_edge(
            mg,
            "package.subpackage.subpackage2.subsubmod",
            "package.subpackage.subpackage2",
            None,
        )
        self.assert_has_edge(
            mg, "package.subpackage.subpackage2", "package.subpackage", None
        )
        self.assert_has_edge(mg, "package.subpackage", "package", None)
        self.assert_has_edge(
            mg,
            "import_two_levels",
            "package.subpackage.submod",
            DependencyInfo(False, False),
        )
        self.assert_has_edge(
            mg, "package.subpackage.submod", "package.subpackage", None
        )
        self.assert_edge_count(mg, 6)

        self.assert_has_roots(mg, "import_two_levels")
        self.assert_has_nodes(
            mg,
            "import_two_levels",
            "package.subpackage.subpackage2.subsubmod",
            "package.subpackage.subpackage2",
            "package.subpackage",
            "package.subpackage.submod",
            "package",
        )

    def test_diamond(self):
        mg = ModuleGraph()
        mg.add_module("diamond_a")

        self.assert_has_node(mg, "diamond_a", SourceModule)
        self.assert_has_node(mg, "diamond_b1", SourceModule)
        self.assert_has_node(mg, "diamond_b2", SourceModule)
        self.assert_has_node(mg, "diamond_c", SourceModule)
        self.assert_has_node(mg, "sys", BuiltinModule)

        self.assert_has_edge(
            mg, "diamond_a", "diamond_b1", DependencyInfo(False, False)
        )
        self.assert_has_edge(
            mg, "diamond_a", "diamond_b2", DependencyInfo(False, False)
        )
        self.assert_has_edge(
            mg, "diamond_b1", "diamond_c", DependencyInfo(False, False)
        )
        self.assert_has_edge(
            mg, "diamond_b2", "diamond_c", DependencyInfo(False, False)
        )
        self.assert_has_edge(mg, "diamond_c", "sys", DependencyInfo(False, False))
        self.assert_edge_count(mg, 5)

        self.assert_has_roots(mg, "diamond_a")
        self.assert_has_nodes(
            mg, "diamond_a", "diamond_b1", "diamond_b2", "diamond_c", "sys"
        )

    def test_alias_import(self):
        mg = ModuleGraph()
        mg.add_module("alias_toplevel")

        self.assert_has_node(mg, "alias_toplevel", SourceModule)
        self.assert_has_node(mg, "alias_import", SourceModule)
        self.assert_has_node(mg, "no_imports", SourceModule)
        self.assert_has_node(mg, "package", Package)
        self.assert_has_node(mg, "package.frommod", SourceModule)
        self.assert_has_node(mg, "package.nosuchmodule", MissingModule)

        self.assert_has_edge(
            mg, "alias_toplevel", "alias_import", DependencyInfo(False, False)
        )
        self.assert_has_edge(
            mg, "alias_import", "no_imports", DependencyInfo(False, False)
        )
        self.assert_has_edge(
            mg, "alias_toplevel", "package.frommod", DependencyInfo(False, True)
        )
        self.assert_has_edge(mg, "package.frommod", "package", None)
        self.assert_has_edge(
            mg, "alias_toplevel", "package.nosuchmodule", DependencyInfo(False, True)
        )
        self.assert_has_edge(mg, "package.nosuchmodule", "package", None)

        self.assert_edge_count(mg, 7)

        self.assert_has_roots(mg, "alias_toplevel")
        self.assert_has_nodes(
            mg,
            "alias_toplevel",
            "alias_import",
            "no_imports",
            "package",
            "package.frommod",
            "package.nosuchmodule",
        )

    # package/__init__.py: import sys
    # toplevel.py: from package import sys
    # -> This should add ref from toplevel top package, no missing node for "package.sys"
    #
    # mod2.py: Define globals a, b
    # package/__init__.py: from mod2 import *
    # toplevel.py: from mod1 import a
    # -> This should work without creating missing nodes (mid item must be package
    #    because from imports from modules are assumed to be correct)
    #
    # Same with extra level of * imports between package and mod2
    #


class TestModuleGraphRelativeImports(unittest.TestCase):
    # Same as previous class, for relative imports
    pass

class TestModuleGraphHooks(unittest.TestCase):
    # Test hooking mechanisms (to be determined)
    pass
