import unittest
import pathlib

import modulegraph2

INPUT_DIR = pathlib.Path(__file__).resolve().parent / "swig-dir"

# XXX: Contextmanager for adjusting sys.path during tests

class TestSWIGSupport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # XXX: Run setup.py in both subdirs
        ...

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

        # XXX: Remove build artifacts from INPUT_DIR


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

    def test_toplevel(self):
        ...

    def test_toplevel_without_hook(self):
        ...

    def test_package(self):
        ...

    def test_package_without_hook(self):
        # XXX: Ensure that the extension module is *not* found
        ...

