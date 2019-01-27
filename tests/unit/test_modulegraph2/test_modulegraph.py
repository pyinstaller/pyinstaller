import unittest
import pathlib
import contextlib
import sys
import os
import importlib
from io import StringIO

from modulegraph2 import (
    Alias,
    AliasNode,
    BuiltinModule,
    DependencyInfo,
    ExcludedModule,
    InvalidRelativeImport,
    MissingModule,
    ModuleGraph,
    NamespacePackage,
    Package,
    PyPIDistribution,
    Script,
    SourceModule,
)

from modulegraph2._packages import distribution_for_file

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

    def test_add_script_twice(self):
        mg = ModuleGraph()
        mg.add_script(INPUT_DIR / "trivial-script")
        self.assertRaises(ValueError, mg.add_script, INPUT_DIR / "trivial-script")

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
            self.assertEqual(len(edge), len(edge_data))
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

    def test_add_module_twice(self):
        with self.subTest("adding root again"):
            mg = ModuleGraph()
            n1 = mg.add_module("no_imports")
            n2 = mg.add_module("no_imports")

            self.assertIs(n1, n2)
            self.assert_has_roots(mg, "no_imports")

        with self.subTest("adding loaded module"):
            mg = ModuleGraph()
            mg.add_module("global_import")
            n1 = mg.find_node("no_imports")
            n2 = mg.add_module("no_imports")

            self.assertIs(n1, n2)
            self.assert_has_roots(mg, "global_import", "no_imports")

    def test_add_module_package(self):
        mg = ModuleGraph()
        mg.add_module("package.submod")
        self.assert_has_node(mg, "package.submod", SourceModule)
        self.assert_has_node(mg, "package", Package)
        self.assert_has_edge(
            mg, "package.submod", "package", {DependencyInfo(False, True, False, None)}
        )

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
            mg,
            "global_import",
            "no_imports",
            {DependencyInfo(False, True, False, None)},
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
            mg, "circular_a", "circular_b", {DependencyInfo(False, True, False, None)}
        )
        self.assert_has_edge(
            mg, "circular_b", "circular_c", {DependencyInfo(False, True, False, None)}
        )
        self.assert_has_edge(
            mg, "circular_c", "circular_a", {DependencyInfo(False, True, False, None)}
        )

        self.assert_edge_count(mg, 3)

        self.assert_has_roots(mg, "circular_a")
        self.assert_has_nodes(mg, "circular_a", "circular_b", "circular_c")

    def test_circular_from(self):
        mg = ModuleGraph()
        mg.add_module("circular_from_a")

        self.assert_has_node(mg, "circular_from_a", SourceModule)
        self.assert_has_node(mg, "circular_from_b", SourceModule)
        self.assert_has_node(mg, "circular_from_c", SourceModule)

        self.assert_has_edge(
            mg,
            "circular_from_a",
            "circular_from_b",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "circular_from_b",
            "circular_from_c",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "circular_from_c",
            "circular_from_a",
            {DependencyInfo(False, True, False, None)},
        )

        self.assert_edge_count(mg, 3)

        self.assert_has_roots(mg, "circular_from_a")
        self.assert_has_nodes(
            mg, "circular_from_a", "circular_from_b", "circular_from_c"
        )

    def test_circular_from_star(self):
        mg = ModuleGraph()
        mg.add_module("circular_from_star_a")

        self.assert_has_node(mg, "circular_from_star_a", SourceModule)
        self.assert_has_node(mg, "circular_from_star_b", SourceModule)
        self.assert_has_node(mg, "circular_from_star_c", SourceModule)

        self.assert_has_edge(
            mg,
            "circular_from_star_a",
            "circular_from_star_b",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "circular_from_star_b",
            "circular_from_star_c",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "circular_from_star_c",
            "circular_from_star_a",
            {DependencyInfo(False, True, False, None)},
        )

        self.assert_edge_count(mg, 3)

        self.assert_has_roots(mg, "circular_from_star_a")
        self.assert_has_nodes(
            mg, "circular_from_star_a", "circular_from_star_b", "circular_from_star_c"
        )

    def test_missing_toplevel(self):
        mg = ModuleGraph()
        mg.add_module("missing")

        self.assert_has_node(mg, "missing", SourceModule)
        self.assert_has_node(mg, "nosuchmodule", MissingModule)

        self.assert_has_edge(
            mg, "missing", "nosuchmodule", {DependencyInfo(False, True, False, None)}
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
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "package.missingmodule",
            "package",
            {DependencyInfo(False, True, False, None)},
        )
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
            mg,
            "missing_package",
            "missingpackage.module",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "missingpackage.module",
            "missingpackage",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_edge_count(mg, 2)

        self.assert_has_roots(mg, "missing_package")
        self.assert_has_nodes(
            mg, "missing_package", "missingpackage", "missingpackage.module"
        )

    def test_missing_nested_package(self):
        mg = ModuleGraph()
        mg.add_module("missing_nested_package")

        self.assert_has_node(mg, "missing_nested_package", SourceModule)
        self.assert_has_node(mg, "missingpackage", MissingModule)
        self.assert_has_node(mg, "missingpackage.missingsubpackage", MissingModule)
        self.assert_has_node(
            mg, "missingpackage.missingsubpackage.module", MissingModule
        )

        self.assert_has_edge(
            mg,
            "missing_nested_package",
            "missingpackage.missingsubpackage.module",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "missingpackage.missingsubpackage.module",
            "missingpackage.missingsubpackage",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "missingpackage.missingsubpackage",
            "missingpackage",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_edge_count(mg, 3)

        self.assert_has_roots(mg, "missing_nested_package")
        self.assert_has_nodes(
            mg,
            "missing_nested_package",
            "missingpackage",
            "missingpackage.missingsubpackage",
            "missingpackage.missingsubpackage.module",
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
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg, "package.submod", "package", {DependencyInfo(False, True, False, None)}
        )
        self.assert_has_edge(
            mg,
            "package.submod",
            "no_imports",
            {DependencyInfo(False, True, False, None)},
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
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg, "package.submod2", "package", {DependencyInfo(False, True, False, None)}
        )
        self.assert_has_edge(
            mg,
            "package.submod2",
            "global_import",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "global_import",
            "no_imports",
            {DependencyInfo(False, True, False, None)},
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
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "package.subpackage.subpackage2.subsubmod",
            "package.subpackage.subpackage2",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "package.subpackage.subpackage2",
            "package.subpackage",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "package.subpackage",
            "package",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "import_two_levels",
            "package.subpackage.submod",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "package.subpackage.submod",
            "package.subpackage",
            {DependencyInfo(False, True, False, None)},
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
            mg, "diamond_a", "diamond_b1", {DependencyInfo(False, True, False, None)}
        )
        self.assert_has_edge(
            mg, "diamond_a", "diamond_b2", {DependencyInfo(False, True, False, None)}
        )
        self.assert_has_edge(
            mg, "diamond_b1", "diamond_c", {DependencyInfo(False, True, False, None)}
        )
        self.assert_has_edge(
            mg, "diamond_b2", "diamond_c", {DependencyInfo(False, True, False, None)}
        )
        self.assert_has_edge(
            mg, "diamond_c", "sys", {DependencyInfo(False, True, False, None)}
        )
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
            mg,
            "alias_toplevel",
            "alias_import",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg, "alias_import", "no_imports", {DependencyInfo(False, True, False, None)}
        )
        self.assert_has_edge(
            mg,
            "alias_toplevel",
            "package.frommod",
            {DependencyInfo(False, True, True, None)},
        )
        self.assert_has_edge(
            mg, "package.frommod", "package", {DependencyInfo(False, True, False, None)}
        )
        self.assert_has_edge(
            mg,
            "alias_toplevel",
            "package.nosuchmodule",
            {DependencyInfo(False, True, True, None)},
        )
        self.assert_has_edge(
            mg,
            "package.nosuchmodule",
            "package",
            {DependencyInfo(False, True, False, None)},
        )

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

    def test_from_sys_import_star(self):
        mg = ModuleGraph()
        mg.add_module("import_sys_star")

        self.assert_has_node(mg, "import_sys_star", SourceModule)
        self.assert_has_node(mg, "sys", BuiltinModule)

        self.assert_has_edge(
            mg, "import_sys_star", "sys", {DependencyInfo(True, True, False, None)}
        )
        self.assert_edge_count(mg, 1)

        self.assert_has_roots(mg, "import_sys_star")
        self.assert_has_nodes(mg, "import_sys_star", "sys")

    def test_package_import_star(self):
        mg = ModuleGraph()
        mg.add_module("from_package_import_star")

        self.assert_has_node(mg, "from_package_import_star", SourceModule)
        self.assert_has_node(mg, "star_package", Package)
        self.assertEqual(
            mg.find_node("from_package_import_star").globals_written,
            mg.find_node("star_package").globals_written,
        )

        self.assert_has_edge(
            mg,
            "from_package_import_star",
            "star_package",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "star_package",
            "star_package.submod",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg, "star_package", "sys", {DependencyInfo(False, True, False, None)}
        )
        self.assert_has_edge(
            mg,
            "star_package.submod",
            "star_package",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_edge_count(mg, 4)

        self.assert_has_roots(mg, "from_package_import_star")
        self.assert_has_nodes(
            mg, "from_package_import_star", "star_package", "star_package.submod", "sys"
        )

    def test_package_import_star2(self):
        mg = ModuleGraph()
        mg.add_module("from_package_import_star2")

        self.assert_has_node(mg, "from_package_import_star2", SourceModule)
        self.assert_has_node(mg, "star_package2", Package)
        self.assertEqual(
            mg.find_node("from_package_import_star2").globals_written,
            mg.find_node("star_package2").globals_written,
        )

        self.assert_has_edge(
            mg,
            "from_package_import_star2",
            "star_package2",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_edge_count(mg, 1)

        self.assert_has_roots(mg, "from_package_import_star2")
        self.assert_has_nodes(mg, "from_package_import_star2", "star_package2")

    def test_from_implicit_import_star(self):
        mg = ModuleGraph()
        mg.add_module("from_implicit_package_import_star")

        self.assert_has_node(mg, "from_implicit_package_import_star", SourceModule)
        self.assert_has_node(mg, "implicit_package", NamespacePackage)

        self.assertEqual(
            mg.find_node("from_implicit_package_import_star").globals_written, set()
        )

        self.assert_has_edge(
            mg,
            "from_implicit_package_import_star",
            "implicit_package",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_edge_count(mg, 1)

        self.assert_has_roots(mg, "from_implicit_package_import_star")
        self.assert_has_nodes(
            mg, "from_implicit_package_import_star", "implicit_package"
        )

    def test_multi_level_star(self):
        mg = ModuleGraph()
        mg.add_module("multi_level_star_import")

        self.assert_has_node(mg, "multi_level_star_import", SourceModule)
        self.assert_has_node(mg, "pkg_a", Package)
        self.assert_has_node(mg, "pkg_b", Package)
        self.assert_has_node(mg, "pkg_c", Package)
        self.assert_has_node(mg, "pkg_d", Package)

        self.assert_has_edge(
            mg,
            "multi_level_star_import",
            "pkg_a",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg, "pkg_a", "pkg_b", {DependencyInfo(False, True, False, None)}
        )
        self.assert_has_edge(
            mg, "pkg_b", "pkg_c", {DependencyInfo(False, True, False, None)}
        )
        self.assert_has_edge(
            mg, "pkg_c", "pkg_d", {DependencyInfo(False, True, False, None)}
        )
        self.assert_edge_count(mg, 4)

        self.assertEqual(mg.find_node("pkg_d").globals_written, {"e"})
        self.assertEqual(mg.find_node("pkg_c").globals_written, {"e"})
        self.assertEqual(mg.find_node("pkg_b").globals_written, {"e"})
        self.assertEqual(mg.find_node("pkg_a").globals_written, {"e"})
        self.assertEqual(
            mg.find_node("from_implicit_package_import_star").globals_written, {"a"}
        )

        self.assert_has_roots(mg, "multi_level_star_import")
        self.assert_has_nodes(
            mg, "multi_level_star_import", "pkg_a", "pkg_b", "pkg_c", "pkg_d"
        )

    def test_multi_level_star(self):
        mg = ModuleGraph()
        mg.add_module("multi_level_star_import2")

        self.assert_has_node(mg, "multi_level_star_import2", SourceModule)
        self.assert_has_node(mg, "pkg_a", Package)
        self.assert_has_node(mg, "pkg_b", Package)
        self.assert_has_node(mg, "pkg_c", Package)
        self.assert_has_node(mg, "pkg_d", Package)

        self.assert_has_edge(
            mg,
            "multi_level_star_import2",
            "pkg_a",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg, "pkg_a", "pkg_b", {DependencyInfo(False, True, False, None)}
        )
        self.assert_has_edge(
            mg, "pkg_b", "pkg_c", {DependencyInfo(False, True, False, None)}
        )
        self.assert_has_edge(
            mg, "pkg_c", "pkg_d", {DependencyInfo(False, True, False, None)}
        )
        self.assert_edge_count(mg, 4)

        self.assertEqual(mg.find_node("pkg_d").globals_written, {"e"})
        self.assertEqual(mg.find_node("pkg_c").globals_written, {"e"})
        self.assertEqual(mg.find_node("pkg_b").globals_written, {"e"})
        self.assertEqual(mg.find_node("pkg_a").globals_written, {"e"})
        self.assertEqual(
            mg.find_node("multi_level_star_import2").globals_written, {"e"}
        )

        self.assert_has_roots(mg, "multi_level_star_import2")
        self.assert_has_nodes(
            mg, "multi_level_star_import2", "pkg_a", "pkg_b", "pkg_c", "pkg_d"
        )

    def test_multi_level_star_import_missing(self):
        mg = ModuleGraph()
        mg.add_module("multi_level_star_import_missing")

        self.assert_has_node(mg, "multi_level_star_import_missing", SourceModule)
        self.assert_has_node(mg, "pkg_c", Package)
        self.assert_has_node(mg, "pkg_d", Package)
        self.assert_has_node(mg, "pkg_c.f", MissingModule)

        self.assert_has_edge(
            mg,
            "multi_level_star_import_missing",
            "pkg_c",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "multi_level_star_import_missing",
            "pkg_c.f",
            {DependencyInfo(False, True, True, None)},
        )
        self.assert_has_edge(
            mg, "pkg_c", "pkg_d", {DependencyInfo(False, True, False, None)}
        )
        self.assert_has_edge(
            mg, "pkg_c.f", "pkg_c", {DependencyInfo(False, True, False, None)}
        )
        self.assert_edge_count(mg, 4)

        self.assertEqual(mg.find_node("pkg_d").globals_written, {"e"})
        self.assertEqual(mg.find_node("pkg_c").globals_written, {"e"})
        self.assertEqual(
            mg.find_node("multi_level_star_import_missing").globals_written, {"f"}
        )

        self.assert_has_roots(mg, "multi_level_star_import_missing")
        self.assert_has_nodes(
            mg, "multi_level_star_import_missing", "pkg_c", "pkg_d", "pkg_c.f"
        )

    def test_imported_aliased_toplevel(self):
        mg = ModuleGraph()
        mg.add_module("imported_aliased_toplevel")

        self.assert_has_node(mg, "imported_aliased_toplevel", SourceModule)
        self.assert_has_node(mg, "aliasing_package", Package)
        self.assert_has_node(mg, "sys", BuiltinModule)
        self.assert_has_node(mg, "no_imports", SourceModule)

        self.assert_has_edge(
            mg,
            "imported_aliased_toplevel",
            "aliasing_package",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg, "aliasing_package", "sys", {DependencyInfo(False, True, False, None)}
        )
        self.assert_has_edge(
            mg,
            "aliasing_package",
            "no_imports",
            {DependencyInfo(False, True, False, None)},  # "Foo"
        )
        self.assert_has_edge(
            mg,
            "imported_aliased_toplevel",
            "sys",
            {DependencyInfo(False, True, True, None)},
        )
        # self.assert_has_edge(
        #    mg,
        #    "imported_aliased_toplevel",
        #    "no_imports",
        #    {DependencyInfo(False, True, True, None)},
        # )
        # self.assert_edge_count(mg, 5)
        self.assert_edge_count(mg, 4)

        self.assert_has_roots(mg, "imported_aliased_toplevel")
        self.assert_has_nodes(
            mg, "imported_aliased_toplevel", "aliasing_package", "sys", "no_imports"
        )

    def test_import_from_package_with_star(self):
        mg = ModuleGraph()
        mg.add_module("import_from_package_with_star")

        self.assert_has_node(mg, "import_from_package_with_star", SourceModule)
        self.assert_has_node(mg, "package_with_star_import", Package)
        self.assert_has_node(mg, "no_imports", SourceModule)

        self.assert_has_edge(
            mg,
            "import_from_package_with_star",
            "package_with_star_import",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "package_with_star_import",
            "no_imports",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_edge_count(mg, 2)

        self.assert_has_roots(mg, "import_from_package_with_star")
        self.assert_has_nodes(
            mg,
            "import_from_package_with_star",
            "package_with_star_import",
            "no_imports",
        )

        self.assertIs(mg.find_node("import_from_package_with_star.a"), None)

    def test_import_from_package_with_star_two_levels(self):
        mg = ModuleGraph()
        mg.add_module("import_from_package_with_star_two_levels")

        self.assert_has_node(
            mg, "import_from_package_with_star_two_levels", SourceModule
        )
        self.assert_has_node(mg, "package_with_star_import2", Package)
        self.assert_has_node(mg, "package_with_star_import", Package)
        self.assert_has_node(mg, "no_imports", SourceModule)

        self.assert_has_edge(
            mg,
            "import_from_package_with_star_two_levels",
            "package_with_star_import2",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "package_with_star_import2",
            "package_with_star_import",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "package_with_star_import",
            "no_imports",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_edge_count(mg, 3)

        self.assert_has_roots(mg, "import_from_package_with_star_two_levels")
        self.assert_has_nodes(
            mg,
            "import_from_package_with_star_two_levels",
            "package_with_star_import2",
            "package_with_star_import",
            "no_imports",
        )

        self.assertIs(mg.find_node("import_from_package_with_star2.a"), None)

    def test_alias_in_sys_modules(self):

        try:
            import no_imports

            sys.modules["there_are_no_imports"] = no_imports

            mg = ModuleGraph()
            mg.add_module("alias_in_sys_modules")

            self.assert_has_roots(mg, "alias_in_sys_modules")
            self.assert_has_nodes(
                mg, "alias_in_sys_modules", "there_are_no_imports", "no_imports"
            )

            self.assert_has_node(mg, "alias_in_sys_modules", SourceModule)
            self.assert_has_node(mg, "there_are_no_imports", AliasNode)
            self.assert_has_node(mg, "no_imports", SourceModule)

            self.assert_has_edge(
                mg,
                "alias_in_sys_modules",
                "there_are_no_imports",
                {DependencyInfo(False, True, False, None)},
            )
            self.assert_has_edge(
                mg,
                "there_are_no_imports",
                "no_imports",
                {DependencyInfo(False, True, False, None)},
            )
            self.assert_edge_count(mg, 2)

        finally:
            del sys.modules["there_are_no_imports"]
            del sys.modules["no_imports"]

    def test_alias_in_sys_modules2(self):

        try:
            import no_imports

            sys.modules["there_are_no_imports"] = no_imports

            mg = ModuleGraph()
            mg.add_module("no_imports")
            mg.add_module("alias_in_sys_modules")

            self.assert_has_roots(mg, "alias_in_sys_modules", "no_imports")
            self.assert_has_nodes(
                mg, "alias_in_sys_modules", "there_are_no_imports", "no_imports"
            )

            self.assert_has_node(mg, "alias_in_sys_modules", SourceModule)
            self.assert_has_node(mg, "there_are_no_imports", AliasNode)
            self.assert_has_node(mg, "no_imports", SourceModule)

            self.assert_has_edge(
                mg,
                "alias_in_sys_modules",
                "there_are_no_imports",
                {DependencyInfo(False, True, False, None)},
            )
            self.assert_has_edge(
                mg,
                "there_are_no_imports",
                "no_imports",
                {DependencyInfo(False, True, False, None)},
            )
            self.assert_edge_count(mg, 2)

        finally:
            del sys.modules["there_are_no_imports"]
            del sys.modules["no_imports"]

    def test_package_without_spec(self):
        # Usecase: fake packages in sys.modules might not
        # have __spec__ and that confuses importlib.util.find_spec

        import without_spec

        mg = ModuleGraph()
        mg.add_module("without_spec.submod")

        self.assert_has_nodes(mg, "without_spec", "without_spec.submod", "no_imports")
        self.assert_has_edge(
            mg,
            "without_spec.submod",
            "without_spec",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "without_spec.submod",
            "no_imports",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_edge_count(mg, 2)

    def test_module_without_spec(self):
        # Usecase: fake packages in sys.modules might not
        # have __spec__ and that confuses importlib.util.find_spec

        import no_imports

        try:
            del no_imports.__spec__

            mg = ModuleGraph()
            mg.add_module("global_import")

            self.assert_has_nodes(mg, "global_import", "no_imports")
            self.assert_has_edge(
                mg,
                "global_import",
                "no_imports",
                {DependencyInfo(False, True, False, None)},
            )
            self.assert_edge_count(mg, 1)
        finally:
            del sys.modules["no_imports"]


class TestModuleGraphRelativeImports(unittest.TestCase):
    # Same as previous class, for relative imports
    def setUp(self):
        sys.path.insert(0, os.fspath(INPUT_DIR))

    def tearDown(self):
        assert sys.path[0] == os.fspath(INPUT_DIR)
        del sys.path[0]

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

    def test_relative_import_toplevel(self):
        mg = ModuleGraph()
        mg.add_module("toplevel_invalid_relative_import")

        self.assert_has_node(mg, "toplevel_invalid_relative_import", SourceModule)
        self.assert_has_node(mg, ".relative", InvalidRelativeImport)

        self.assert_has_edge(
            mg,
            "toplevel_invalid_relative_import",
            ".relative",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_edge_count(mg, 1)

        self.assert_has_nodes(mg, "toplevel_invalid_relative_import", ".relative")

    def test_relative_import_toplevel_multiple(self):
        mg = ModuleGraph()
        mg.add_module("toplevel_invalid_relative_import_multiple")

        self.assert_has_node(
            mg, "toplevel_invalid_relative_import_multiple", SourceModule
        )
        self.assert_has_node(mg, ".relative", InvalidRelativeImport)

        self.assert_has_edge(
            mg,
            "toplevel_invalid_relative_import_multiple",
            ".relative",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_edge_count(mg, 1)

        self.assert_has_nodes(
            mg, "toplevel_invalid_relative_import_multiple", ".relative"
        )

    def test_relative_import_to_outside_package(self):
        mg = ModuleGraph()
        mg.add_module("package_invalid_relative_import")

        self.assert_has_node(mg, "package_invalid_relative_import", SourceModule)
        self.assert_has_node(mg, "invalid_relative_package", Package)
        self.assert_has_node(mg, "..relative", InvalidRelativeImport)

        self.assert_has_edge(
            mg,
            "package_invalid_relative_import",
            "invalid_relative_package",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "invalid_relative_package",
            "..relative",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_edge_count(mg, 2)

        self.assert_has_nodes(
            mg,
            "package_invalid_relative_import",
            "invalid_relative_package",
            "..relative",
        )

    def test_global_import(self):
        mg = ModuleGraph()
        mg.add_module("basic_relative_import")

        self.assert_has_node(mg, "basic_relative_import", SourceModule)
        self.assert_has_node(mg, "package", Package)
        self.assert_has_node(mg, "package.relative", SourceModule)
        self.assert_has_node(mg, "package.submod", SourceModule)
        self.assert_has_node(mg, "no_imports", SourceModule)

        self.assert_has_edge(
            mg,
            "basic_relative_import",
            "package.relative",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "package.relative",
            "package",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "package.relative",
            "package.submod",
            {DependencyInfo(False, True, True, None)},
        )
        self.assert_has_edge(
            mg, "package.submod", "package", {DependencyInfo(False, True, False, None)}
        )
        self.assert_has_edge(
            mg,
            "package.submod",
            "no_imports",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_edge_count(mg, 5)

        self.assert_has_nodes(
            mg,
            "basic_relative_import",
            "package",
            "package.relative",
            "package.submod",
            "no_imports",
        )

    def test_circular_imports(self):
        mg = ModuleGraph()
        mg.add_module("circular_relative")

        self.assert_has_node(mg, "circular_relative", SourceModule)
        self.assert_has_node(mg, "package.circular_a", SourceModule)
        self.assert_has_node(mg, "package.circular_b", SourceModule)
        self.assert_has_node(mg, "package.circular_c", SourceModule)

        self.assert_has_edge(
            mg,
            "circular_relative",
            "package.circular_a",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "package.circular_a",
            "package",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "package.circular_b",
            "package",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "package.circular_c",
            "package",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "package.circular_a",
            "package.circular_b",
            {DependencyInfo(False, True, True, None)},
        )
        self.assert_has_edge(
            mg,
            "package.circular_b",
            "package.circular_c",
            {DependencyInfo(False, True, True, None)},
        )
        self.assert_has_edge(
            mg,
            "package.circular_c",
            "package.circular_a",
            {DependencyInfo(False, True, True, None)},
        )

        self.assert_edge_count(mg, 7)

        self.assert_has_roots(mg, "circular_relative")
        self.assert_has_nodes(
            mg,
            "circular_relative",
            "package",
            "package.circular_a",
            "package.circular_b",
            "package.circular_c",
        )

    def test_missing_relative(self):
        mg = ModuleGraph()
        mg.add_module("missing_relative")

        self.assert_has_node(mg, "missing_relative", SourceModule)
        self.assert_has_node(mg, "package", Package)
        self.assert_has_node(mg, "package.missing_relative", SourceModule)
        self.assert_has_node(mg, "package.nosuchmodule", MissingModule)

        self.assert_has_edge(
            mg,
            "missing_relative",
            "package.missing_relative",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "package.missing_relative",
            "package",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "package.nosuchmodule",
            "package",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "package.missing_relative",
            "package.nosuchmodule",
            {DependencyInfo(False, True, True, None)},
        )
        self.assert_edge_count(mg, 4)

        self.assert_has_roots(mg, "missing_relative")
        self.assert_has_nodes(
            mg,
            "missing_relative",
            "package",
            "package.missing_relative",
            "package.nosuchmodule",
        )

    def test_missing_package(self):
        mg = ModuleGraph()
        mg.add_module("missing_relative_package")

        self.assert_has_nodes(
            mg,
            "missing_relative_package",
            "relative_package_with_missing",
            "relative_package_with_missing.package",
            "relative_package_with_missing.package.subpackage",
        )

        # The "from" imported names aren't in the graph because MG
        # doesn't know if the MissingModules are packages. The current
        # behaviour results in cleaner graphs.
        #

        self.assert_has_node(mg, "missing_relative_package", SourceModule)
        self.assert_has_node(mg, "relative_package_with_missing", Package)
        self.assert_has_node(mg, "relative_package_with_missing.package", MissingModule)
        self.assert_has_node(
            mg, "relative_package_with_missing.package.subpackage", MissingModule
        )

        self.assert_has_edge(
            mg,
            "missing_relative_package",
            "relative_package_with_missing",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "relative_package_with_missing",
            "relative_package_with_missing.package",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "relative_package_with_missing",
            "relative_package_with_missing.package.subpackage",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "relative_package_with_missing.package",
            "relative_package_with_missing",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "relative_package_with_missing.package.subpackage",
            "relative_package_with_missing.package",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_edge_count(mg, 5)

    def test_multiple_imports(self):
        mg = ModuleGraph()
        mg.add_module("multiple_relative_imports")

        self.assert_has_nodes(
            mg,
            "multiple_relative_imports",
            "package",
            "package.multiple_relative",
            "package.submod",
            "no_imports",
        )

        self.assert_has_node(mg, "multiple_relative_imports", SourceModule)
        self.assert_has_node(mg, "package", Package)
        self.assert_has_node(mg, "package.multiple_relative", SourceModule)
        self.assert_has_node(mg, "package.submod", SourceModule)
        self.assert_has_node(mg, "no_imports", SourceModule)

        self.assert_has_edge(
            mg,
            "multiple_relative_imports",
            "package",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "multiple_relative_imports",
            "package.multiple_relative",
            {DependencyInfo(False, True, True, None)},
        )
        self.assert_has_edge(
            mg,
            "package.multiple_relative",
            "package.submod",
            {
                DependencyInfo(False, True, True, None),
                DependencyInfo(True, True, True, None),
            },
        )
        self.assert_has_edge(
            mg,
            "package.multiple_relative",
            "package",
            {
                DependencyInfo(False, True, False, None),
                DependencyInfo(True, True, False, None),
            },
        )
        self.assert_has_edge(
            mg, "package.submod", "package", {DependencyInfo(False, True, False, None)}
        )
        self.assert_has_edge(
            mg,
            "package.submod",
            "no_imports",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_edge_count(mg, 6)

    def test_diamond(self):
        mg = ModuleGraph()
        mg.add_module("package_diamond")

        self.assert_has_node(mg, "package_diamond", SourceModule)
        self.assert_has_node(mg, "package", Package)
        self.assert_has_node(mg, "package.diamond_a", SourceModule)
        self.assert_has_node(mg, "package.diamond_b1", SourceModule)
        self.assert_has_node(mg, "package.diamond_b2", SourceModule)
        self.assert_has_node(mg, "package.diamond_c", SourceModule)
        self.assert_has_node(mg, "sys", BuiltinModule)

        self.assert_has_edge(
            mg,
            "package_diamond",
            "package.diamond_a",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "package.diamond_a",
            "package.diamond_b1",
            {DependencyInfo(False, True, True, None)},
        )
        self.assert_has_edge(
            mg,
            "package.diamond_a",
            "package.diamond_b2",
            {DependencyInfo(False, True, True, None)},
        )
        self.assert_has_edge(
            mg,
            "package.diamond_b1",
            "package.diamond_c",
            {DependencyInfo(False, True, True, None)},
        )
        self.assert_has_edge(
            mg,
            "package.diamond_b2",
            "package.diamond_c",
            {DependencyInfo(False, True, True, None)},
        )
        self.assert_has_edge(
            mg, "package.diamond_c", "sys", {DependencyInfo(False, True, False, None)}
        )
        self.assert_has_edge(
            mg,
            "package.diamond_a",
            "package",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "package.diamond_b1",
            "package",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "package.diamond_b2",
            "package",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "package.diamond_c",
            "package",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_edge_count(mg, 10)

        self.assert_has_roots(mg, "package_diamond")
        self.assert_has_nodes(
            mg,
            "package_diamond",
            "package",
            "package.diamond_a",
            "package.diamond_b1",
            "package.diamond_b2",
            "package.diamond_c",
            "sys",
        )

    def test_alias_import(self):
        mg = ModuleGraph()
        mg.add_module("aliasing_relative")

        self.assert_has_node(mg, "aliasing_relative", SourceModule)
        self.assert_has_node(mg, "package", Package)
        self.assert_has_node(mg, "package.aliasing_relative", SourceModule)
        self.assert_has_node(mg, "package.submod", SourceModule)
        self.assert_has_node(mg, "no_imports", SourceModule)

        self.assert_has_edge(
            mg,
            "aliasing_relative",
            "package.aliasing_relative",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "package.aliasing_relative",
            "package.submod",
            {DependencyInfo(False, True, True, None)},
        )
        self.assert_has_edge(
            mg,
            "package.aliasing_relative",
            "package",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg, "package.submod", "package", {DependencyInfo(False, True, False, None)}
        )
        self.assert_has_edge(
            mg,
            "package.submod",
            "no_imports",
            {DependencyInfo(False, True, False, None)},
        )

        self.assert_edge_count(mg, 5)

        self.assert_has_roots(mg, "aliasing_relative")
        self.assert_has_nodes(
            mg,
            "aliasing_relative",
            "package",
            "package.aliasing_relative",
            "package.submod",
            "no_imports",
        )


class TestModuleGraphHooks(unittest.TestCase):
    # Test hooking mechanisms (to be determined)
    #
    # Probably need callbacks:
    # - Before creating a mssing node, callback returns Optional[BaseNode]
    #   (What is the use case?)
    #
    # - After adding a new PyPIDistribution,
    #   Use case: add implied data for this distribution in recipe
    #
    # - After a node is "finished"
    #   Use case: Adjust graph for this node (py2app recipes)
    #
    # - Debugging?
    #   It can be helpfull to log what the graph builder is doing
    #
    # All of these are lists of callbacks that will all be called.
    #
    # Mechanism for updating _lazy_nodes:
    # 1) def update_implies(self, new): self._lazy_nodes.update(new)
    # 2) def exclude_module(self, name): ...
    # 3) def add_module_alias(self, name): ...
    def setUp(self):
        sys.path.insert(0, os.fspath(INPUT_DIR))

    def tearDown(self):
        assert sys.path[0] == os.fspath(INPUT_DIR)
        del sys.path[0]

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
            self.assertEqual(len(edge), len(edge_data))
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

    def test_post_processing(self):
        # This adds a number of other test modules to verify
        # that the post processing hook is called when needed.
        nodes_processed = set()

        def hook(graph, node):
            nodes_processed.add(node.identifier)

        mg = ModuleGraph()
        mg.add_post_processing_hook(hook)

        mg.add_module("global_import")
        mg.add_module("nosuchmodule")
        mg.add_module("missing_in_package")
        mg.add_module("missing_relative")
        mg.add_module("toplevel_invalid_relative_import")
        mg.add_script(INPUT_DIR / "trivial-script")
        self.assertEqual(
            nodes_processed,
            {
                "global_import",
                "no_imports",
                "nosuchmodule",
                os.fspath(INPUT_DIR / "trivial-script"),
                "missing_in_package",
                "package",
                "package.missingmodule",
                "package.nosuchmodule",
                "package.missing_relative",
                "missing_relative",
                "toplevel_invalid_relative_import",
                ".relative",
            },
        )

    def test_excluded_module(self):
        mg = ModuleGraph()
        mg.add_excludes(["global_import"])

        mg.add_module("excluded_import")

        self.assert_has_nodes(mg, "excluded_import", "global_import")
        self.assert_has_node(mg, "global_import", ExcludedModule)
        self.assert_has_edge(
            mg,
            "excluded_import",
            "global_import",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_edge_count(mg, 1)

        self.assertRaises(TypeError, mg.add_excludes, "some_name")

    def test_excluded_package(self):
        mg = ModuleGraph()
        mg.add_excludes(["package"])

        mg.add_module("package_import_single_level")

        self.assert_has_nodes(
            mg, "package_import_single_level", "package", "package.submod"
        )

        self.assert_has_node(mg, "package", ExcludedModule)
        self.assert_has_node(mg, "package.submod", ExcludedModule)

        self.assert_has_edge(
            mg,
            "package_import_single_level",
            "package.submod",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg, "package.submod", "package", {DependencyInfo(False, True, False, None)}
        )
        self.assert_edge_count(mg, 2)

    def test_implied_stdlib(self):

        with self.subTest("using implies"):
            mg = ModuleGraph()
            mg.add_module("_curses")

            self.assert_has_node(mg, "_curses")
            self.assert_has_node(mg, "curses")
            self.assert_has_edge(
                mg, "_curses", "curses", {DependencyInfo(False, True, False, None)}
            )

        with self.subTest("without implies"):
            mg = ModuleGraph(use_stdlib_implies=False)
            mg.add_module("_curses")

            self.assert_has_node(mg, "_curses")
            self.assertIs(mg.find_node("curses"), None)

    def test_implied_imports(self):
        mg = ModuleGraph()
        mg.add_implies({"no_imports": ("sys", "gc"), "global_import": ("marshal",)})

        mg.add_module("import_with_implies")

        self.assert_has_nodes(
            mg,
            "import_with_implies",
            "no_imports",
            "global_import",
            "sys",
            "gc",
            "marshal",
        )
        self.assert_has_roots(mg, "import_with_implies")

        self.assert_has_edge(
            mg,
            "import_with_implies",
            "no_imports",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "import_with_implies",
            "global_import",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg, "no_imports", "sys", {DependencyInfo(False, True, False, None)}
        )
        self.assert_has_edge(
            mg, "no_imports", "gc", {DependencyInfo(False, True, False, None)}
        )
        self.assert_has_edge(
            mg,
            "global_import",
            "no_imports",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg, "global_import", "marshal", {DependencyInfo(False, True, False, None)}
        )
        self.assert_edge_count(mg, 6)

    def test_implies_to_package(self):
        mg = ModuleGraph()
        mg.add_implies({"no_imports": ("package.submod",)})

        mg.add_module("global_import")

        self.assert_has_edge(
            mg,
            "no_imports",
            "package.submod",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg, "package.submod", "package", {DependencyInfo(False, True, False, None)}
        )

    def test_implies_vs_add_module(self):
        mg = ModuleGraph()
        mg.add_implies({"no_imports": ("marshal",)})

        mg.add_module("no_imports")

        self.assert_has_edge(
            mg, "no_imports", "marshal", {DependencyInfo(False, True, False, None)}
        )

    def test_implies_vs_import_module(self):
        mg = ModuleGraph()
        mg.add_implies({"no_imports": ("marshal",)})

        node = MissingModule("missing")
        mg.add_node(node)
        mg.add_root(node)

        mg.import_module(node, "no_imports")
        mg._run_q()  # XXX: Private API

        self.assert_has_edge(
            mg, "no_imports", "marshal", {DependencyInfo(False, True, False, None)}
        )

    def test_implies_vs_excludes(self):

        mg = ModuleGraph()
        mg.add_excludes(["no_imports"])
        mg.add_implies({"no_imports": ("sys",)})

        mg.add_module("global_import")
        self.assert_has_node(mg, "no_imports", ExcludedModule)
        self.assert_has_nodes(mg, "global_import", "no_imports")

    def test_implies_vs_excludes2(self):

        mg = ModuleGraph()
        mg.add_implies({"no_imports": ("sys",)})
        mg.add_excludes(["no_imports"])

        mg.add_module("global_import")
        self.assert_has_node(mg, "no_imports", ExcludedModule)
        self.assert_has_nodes(mg, "global_import", "no_imports")

    def test_implies_order(self):
        mg = ModuleGraph()
        mg.add_implies({"no_imports": ("sys",)})
        mg.add_module("sys")
        mg.add_module("global_import")

        self.assert_has_nodes(mg, "global_import", "no_imports", "sys")
        self.assert_has_node(mg, "no_imports", SourceModule)

        self.assert_has_edge(
            mg, "no_imports", "sys", {DependencyInfo(False, True, False, None)}
        )

    def test_alias(self):
        mg = ModuleGraph()
        mg.add_implies({"no_imports": Alias("marshal")})

        mg.add_module("global_import")

        self.assert_has_nodes(mg, "global_import", "no_imports", "marshal")
        self.assert_has_node(mg, "no_imports", AliasNode)

        self.assert_has_edge(
            mg,
            "global_import",
            "no_imports",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg, "no_imports", "marshal", {DependencyInfo(False, True, False, None)}
        )

    def test_alias_to_package(self):
        mg = ModuleGraph()
        mg.add_implies({"no_imports": Alias("package.submod")})

        mg.add_module("global_import")

        self.assert_has_nodes(
            mg, "global_import", "no_imports", "package", "package.submod"
        )
        self.assert_has_node(mg, "no_imports", AliasNode)

        self.assert_has_edge(
            mg,
            "global_import",
            "no_imports",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "no_imports",
            "package.submod",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg, "package.submod", "package", {DependencyInfo(False, True, False, None)}
        )

    def test_alias_to_package_import_from(self):
        mg = ModuleGraph()
        mg.add_implies({"the_package": Alias("package")})

        mg.add_module("alias_to_package_import_from")

        self.assert_has_node(mg, "the_package", AliasNode)
        self.assert_has_node(mg, "package", Package)
        self.assert_has_edge(
            mg, "the_package", "package", {DependencyInfo(False, True, False, None)}
        )

        self.assert_has_nodes(
            mg,
            "alias_to_package_import_from",
            "the_package",
            "package",
            "package.submod",
            "no_imports",
        )

        self.assert_has_node(mg, "alias_to_package_import_from", SourceModule)
        self.assert_has_node(mg, "the_package", AliasNode)
        self.assert_has_node(mg, "package", Package)
        self.assert_has_node(mg, "package.submod", SourceModule)
        self.assert_has_node(mg, "no_imports", SourceModule)

        self.assert_has_edge(
            mg,
            "alias_to_package_import_from",
            "the_package",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg, "the_package", "package", {DependencyInfo(False, True, False, None)}
        )
        self.assert_has_edge(
            mg,
            "alias_to_package_import_from",
            "package.submod",
            {DependencyInfo(False, True, True, None)},
        )
        self.assert_has_edge(
            mg, "package.submod", "package", {DependencyInfo(False, True, False, None)}
        )
        self.assert_has_edge(
            mg,
            "package.submod",
            "no_imports",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_edge_count(mg, 5)

    def test_alias_to_module_import_from(self):
        mg = ModuleGraph()
        mg.add_implies({"the_package": Alias("no_imports")})

        mg.add_module("alias_to_module_import_from")

        self.assert_has_nodes(
            mg, "alias_to_module_import_from", "the_package", "no_imports"
        )

        self.assert_has_node(mg, "alias_to_module_import_from", SourceModule)
        self.assert_has_node(mg, "the_package", AliasNode)
        self.assert_has_node(mg, "no_imports", SourceModule)

        self.assert_has_edge(
            mg,
            "alias_to_module_import_from",
            "the_package",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg, "the_package", "no_imports", {DependencyInfo(False, True, False, None)}
        )
        self.assert_edge_count(mg, 2)

    def test_alias_order(self):
        mg = ModuleGraph()
        mg.add_implies({"no_imports": Alias("marshal")})

        mg.add_module("marshal")
        mg.add_module("global_import")

        self.assert_has_nodes(mg, "global_import", "no_imports", "marshal")
        self.assert_has_node(mg, "no_imports", AliasNode)

        self.assert_has_edge(
            mg,
            "global_import",
            "no_imports",
            {DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg, "no_imports", "marshal", {DependencyInfo(False, True, False, None)}
        )

    def test_import_module(self):
        mg = ModuleGraph()

        node = MissingModule("missing")
        mg.add_node(node)
        mg.add_root(node)

        mg.import_module(node, "no_imports")

        self.assert_has_edge(
            mg, "missing", "no_imports", {DependencyInfo(False, True, False, None)}
        )

    def test_import_module_existing(self):
        mg = ModuleGraph()

        node = MissingModule("missing")
        mg.add_node(node)
        mg.add_root(node)
        mg.add_module("no_imports")

        mg.import_module(node, "no_imports")

        self.assert_has_edge(
            mg, "missing", "no_imports", {DependencyInfo(False, True, False, None)}
        )

    def test_import_module_twice(self):
        mg = ModuleGraph()

        node = MissingModule("missing")
        mg.add_node(node)
        mg.add_root(node)

        mg.import_module(node, "no_imports")
        mg.import_module(node, "no_imports")

        self.assert_has_edge(
            mg, "missing", "no_imports", {DependencyInfo(False, True, False, None)}
        )

    def test_import_module_package(self):
        mg = ModuleGraph()

        node = MissingModule("missing")
        mg.add_node(node)
        mg.add_root(node)

        mg.import_module(node, "package.submod")

        self.assert_has_edge(
            mg, "missing", "package.submod", {DependencyInfo(False, True, False, None)}
        )
        self.assert_has_edge(
            mg, "package.submod", "package", {DependencyInfo(False, True, False, None)}
        )

    def test_using_missing_hook(self):

        missing = set()

        def missing_hook(graph, importing_module, module_name):
            missing.add(module_name)
            node = InvalidRelativeImport(module_name)
            graph.add_node(node)
            return node

        mg = ModuleGraph(use_builtin_hooks=False)
        mg.add_missing_hook(missing_hook)

        mg.add_module("missing")

        self.assertEqual(missing, {"nosuchmodule"})

        self.assert_has_node(mg, "missing", SourceModule)
        self.assert_has_node(mg, "nosuchmodule", InvalidRelativeImport)
        self.assert_has_edge(
            mg, "missing", "nosuchmodule", {DependencyInfo(False, True, False, None)}
        )

        # XXX: need to test for the correct "importing_module" as well (for various cases)


REPORT_HEADER = """
Class           Name                      File
-----           ----                      ----
"""


class TestModuleGraphQuerying(unittest.TestCase):
    #
    # Tests for APIs that query the graph (other than those inherited from ObjectGraph)
    #

    def test_distributions_empty(self):
        mg = ModuleGraph()
        self.assertEqual(set(mg.distributions()), set())

        n1 = MissingModule("n1")
        mg.add_node(n1)
        mg.add_root(n1)

        self.assertEqual(set(mg.distributions()), set())

    def test_distributions_real(self):
        import pip

        mg = ModuleGraph()
        node = MissingModule("nosuchmodule")
        node.distribution = distribution_for_file(pip.__file__, sys.path)
        self.assertIsNot(node.distribution, None)

        mg.add_node(node)
        result = list(mg.distributions())
        self.assertEqual(len(result), 0)

        result = list(mg.distributions(False))
        self.assertEqual(len(result), 1)

        self.assertIsInstance(result[0], PyPIDistribution)
        self.assertEqual(result[0].name, "pip")

        mg.add_root(node)
        result = list(mg.distributions())

        self.assertIsInstance(result[0], PyPIDistribution)
        self.assertEqual(result[0].name, "pip")

    def test_some_distributions(self):
        def make_distribution(name):
            return PyPIDistribution(name, name, "", set(), set())

        mg = ModuleGraph()

        n1 = MissingModule("n1")
        n2 = MissingModule("n2")
        n3 = MissingModule("n3")

        n1.distribution = n2.distribution = n3.distribution = make_distribution("dist1")

        mg.add_node(n1)
        mg.add_node(n2)
        mg.add_node(n3)

        mg.add_root(n1)
        mg.add_root(n2)
        mg.add_root(n3)

        result = list(mg.distributions())
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "dist1")

        n4 = MissingModule("n4")
        n4.distribution = make_distribution("dist2")

        mg.add_node(n4)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "dist1")

        mg.add_root(n4)

        result = list(mg.distributions())
        self.assertEqual(len(result), 2)
        self.assertEqual({d.name for d in result}, {"dist1", "dist2"})

    def test_report_empty(self):
        mg = ModuleGraph()

        fp = StringIO()

        mg.report(fp)
        self.assertEqual(fp.getvalue(), REPORT_HEADER)

    def test_report_unreachable(self):
        mg = ModuleGraph()

        fp = StringIO()

        mg.add_node(MissingModule("n1"))

        mg.report(fp)
        self.assertEqual(fp.getvalue(), REPORT_HEADER)

    def test_report_one(self):
        mg = ModuleGraph()

        fp = StringIO()

        n1 = MissingModule("n1")
        n1.filename = "FILE"
        mg.add_node(n1)
        mg.add_root(n1)

        mg.report(fp)
        self.assertEqual(
            fp.getvalue(),
            REPORT_HEADER + "MissingModule   n1                        FILE\n",
        )


class TestModuleGraphTools(unittest.TestCase):
    # Not sure yet if these need to be in modulegraph2, and if so
    # where these need to end up

    # 1) Utility that ensure that entire PyPIDistributions get inclded
    #    (with correct updates of the graph)
    #
    # 2) Likewise for packages
    pass
