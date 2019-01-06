import unittest
import pathlib
import contextlib

from modulegraph2 import ModuleGraph, Script, SourceModule

INPUT_DIR = pathlib.Path(__file__).resolve().parent / "modulegraph-dir"


class TestModuleGraph(unittest.TestCase):
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

    def test_stdlib_script(self):
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
