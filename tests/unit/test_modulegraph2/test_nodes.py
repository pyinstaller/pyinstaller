import unittest
import os
from modulegraph2 import _nodes as nodes
import importlib.util
import pathlib

loader = importlib.util.find_spec("os").loader
file_path = pathlib.Path(__file__).resolve()


class TestNodes(unittest.TestCase):
    def test_basenode(self):
        n = nodes.BaseNode(
            name="basenode",
            loader=loader,
            distribution=None,
            filename=file_path,
            extension_attributes={},
        )

        self.assertEqual(n.name, "basenode")
        self.assertEqual(n.identifier, "basenode")
        self.assertIs(n.loader, loader)
        self.assertIs(n.distribution, None)
        self.assertIs(n.filename, file_path)
        self.assertEqual(n.extension_attributes, {})

    def test_script(self):
        # Use the full name of an existing script to avoid problems
        # on Windows
        n = nodes.Script(
            pathlib.Path(__file__).parent / "modulegraph-dir" / "trivial-script"
        )
        self.assertEqual(
            n.name,
            os.fspath(
                pathlib.Path(__file__).parent / "modulegraph-dir" / "trivial-script"
            ),
        )
        self.assertEqual(
            n.filename,
            pathlib.Path(__file__).parent / "modulegraph-dir" / "trivial-script",
        )

        self.assertIs(n.loader, None)
        self.assertIs(n.distribution, None)
        self.assertEqual(n.extension_attributes, {})

    def test_alias_node(self):
        n = nodes.AliasNode("imported_name", "alias_name")
        self.assertEqual(n.name, "imported_name")
        self.assertEqual(n.actual_module, "alias_name")

        self.assertIs(n.loader, None)
        self.assertIs(n.filename, None)
        self.assertIs(n.distribution, None)
        self.assertEqual(n.extension_attributes, {})

    def test_virtual_node(self):
        n = nodes.VirtualNode("imported_name", "providing_name")
        self.assertEqual(n.name, "imported_name")
        self.assertEqual(n.providing_module, "providing_name")

        self.assertIs(n.loader, None)
        self.assertIs(n.filename, None)
        self.assertIs(n.distribution, None)
        self.assertEqual(n.extension_attributes, {})

    def test_missing_module(self):
        n = nodes.MissingModule("imported_name")
        self.assertEqual(n.name, "imported_name")

        self.assertIs(n.loader, None)
        self.assertIs(n.filename, None)
        self.assertIs(n.distribution, None)
        self.assertEqual(n.extension_attributes, {})

    def test_invalid_relative_import(self):
        n = nodes.InvalidRelativeImport("imported_name")
        self.assertEqual(n.name, "imported_name")

        self.assertIs(n.loader, None)
        self.assertIs(n.filename, None)
        self.assertIs(n.distribution, None)
        self.assertEqual(n.extension_attributes, {})

    def test_excluded_module(self):
        n = nodes.ExcludedModule("imported_name")
        self.assertEqual(n.name, "imported_name")

        self.assertIs(n.loader, None)
        self.assertIs(n.filename, None)
        self.assertIs(n.distribution, None)
        self.assertEqual(n.extension_attributes, {})

    def test_modules(self):
        for cls in (
            nodes.Module,
            nodes.SourceModule,
            nodes.BytecodeModule,
            nodes.ExtensionModule,
            nodes.BuiltinModule,
        ):
            with self.subTest(cls.__name__):
                n = cls(
                    name="module",
                    loader=loader,
                    distribution=None,
                    filename=file_path,
                    extension_attributes={},
                    globals_written={"a", "b", "c"},
                    globals_read={"c", "d"},
                )

                self.assertEqual(n.name, "module")
                self.assertIs(n.loader, loader)
                self.assertIs(n.distribution, None)
                self.assertIs(n.filename, file_path)
                self.assertEqual(n.extension_attributes, {})
                self.assertEqual(n.globals_written, {"a", "b", "c"})
                self.assertEqual(n.globals_read, {"c", "d"})

                self.assertFalse(n.uses_dunder_import)
                self.assertFalse(n.uses_dunder_file)

                n.globals_read.add("__file__")
                self.assertFalse(n.uses_dunder_import)
                self.assertTrue(n.uses_dunder_file)

                n.globals_read.add("__import__")
                self.assertTrue(n.uses_dunder_import)
                self.assertTrue(n.uses_dunder_file)

                n.globals_read.remove("__file__")
                self.assertTrue(n.uses_dunder_import)
                self.assertFalse(n.uses_dunder_file)

    def test_namespace_package(self):
        n = nodes.NamespacePackage(
            name="module",
            loader=loader,
            distribution=None,
            filename=file_path,
            extension_attributes={},
            search_path=[1, 2],
            has_data_files=False,
        )

        self.assertEqual(n.name, "module")
        self.assertIs(n.loader, loader)
        self.assertIs(n.distribution, None)
        self.assertIs(n.filename, file_path)
        self.assertEqual(n.extension_attributes, {})
        self.assertEqual(n.search_path, [1, 2])
        self.assertEqual(n.has_data_files, False)
        self.assertEqual(n.globals_written, frozenset())
        self.assertEqual(n.globals_read, frozenset())
        self.assertTrue(isinstance(n.globals_written, frozenset))
        self.assertTrue(isinstance(n.globals_read, frozenset))

    def test_package(self):
        m = nodes.SourceModule(
            name="module",
            loader=loader,
            distribution=None,
            filename=file_path,
            extension_attributes={},
            globals_written={"a"},
            globals_read={"b"},
        )

        n = nodes.Package(
            name="module",
            loader=loader,
            distribution=None,
            filename=file_path,
            extension_attributes={},
            init_module=m,
            search_path=[1, 2],
            has_data_files=True,
            namespace_type="bar",
        )

        self.assertEqual(n.name, "module")
        self.assertIs(n.loader, loader)
        self.assertIs(n.distribution, None)
        self.assertIs(n.filename, file_path)
        self.assertEqual(n.extension_attributes, {})
        self.assertIs(n.init_module, m)
        self.assertEqual(n.search_path, [1, 2])
        self.assertEqual(n.has_data_files, True)
        self.assertEqual(n.namespace_type, "bar")

        self.assertEqual(n.globals_written, {"a"})
        self.assertEqual(n.globals_read, {"b"})
