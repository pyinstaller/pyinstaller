"""
Testing utilities
"""
import sys
import os
import importlib

from modulegraph2 import Script


def clear_sys_modules(test_path):
    to_remove = []
    for mod in sys.modules:
        if (
            hasattr(sys.modules[mod], "__file__")
            and sys.modules[mod].__file__ is not None
            and sys.modules[mod].__file__.startswith(os.fspath(test_path))
        ):
            to_remove.append(mod)
    for mod in to_remove:
        del sys.modules[mod]

    importlib.invalidate_caches()


class TestMixin:
    def assert_valid_script_node(self, node, script_file):
        self.assertIsInstance(node, Script)
        self.assertEqual(node.name, str(script_file))
        self.assertEqual(node.filename, script_file)
        self.assertIs(node.distribution, None)
        self.assertIs(node.loader, None)
        self.assertEqual(node.extension_attributes, {})

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
            if edge_data is not None:
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
