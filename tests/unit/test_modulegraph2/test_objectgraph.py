import unittest

import modulegraph2


class Node(object):
    def __init__(self, identifier):
        self.identifier = identifier

    def __repr__(self):
        return f"<node {self.identifier!r}>"


class TestObjectGraph(unittest.TestCase):
    def test_empty(self):
        graph = modulegraph2.ObjectGraph()

        self.assertEqual(repr(graph), "<ObjectGraph with 0 roots, 0 nodes and 0 edges>")

        self.assertEqual(list(graph.roots()), [])
        self.assertEqual(list(graph.nodes()), [])
        self.assertEqual(list(graph.edges()), [])
        self.assertEqual(list(graph.iter_graph()), [])

        self.assertFalse("foo" in graph)
        self.assertEqual(graph.find_node("foo"), None)
        self.assertEqual(list(graph.incoming("foo")), [])
        self.assertEqual(list(graph.outgoing("foo")), [])

    def test_simple_graph(self):
        graph = modulegraph2.ObjectGraph()

        n1 = Node("n1")
        n2 = Node("n2")
        n3 = Node("n3")
        n4 = Node("n4")

        graph.add_node(n1)
        graph.add_node(n2)
        graph.add_node(n3)

        self.assertEqual(set(graph.nodes()), {n1, n2, n3})
        self.assertEqual(set(graph.roots()), set())
        self.assertEqual(list(graph.edges()), [])

        graph.add_root(n2)
        self.assertEqual(set(graph.roots()), {n2})

        self.assertRaises(KeyError, graph.add_root, n4)

        self.assertRaises(KeyError, graph.edge_data, n1, n2)

        self.assertEqual(set(graph.outgoing(n1)), set())
        self.assertEqual(set(graph.incoming(n1)), set())

        graph.add_edge(n1, n2, 42)

        self.assertEqual(set(graph.outgoing(n1)), {(42, n2)})
        self.assertEqual(set(graph.incoming(n1)), set())
        self.assertEqual(set(graph.edges()), {(n1, n2, 42)})

        self.assertRaises(ValueError, graph.add_edge, n1, n2, 21)

        self.assertEqual(set(graph.outgoing(n1)), {(42, n2)})
        self.assertEqual(set(graph.incoming(n1)), set())

        graph.add_edge(n1, n2, 21, lambda a, b: a + b)

        self.assertEqual(set(graph.outgoing(n1)), {(63, n2)})
        self.assertEqual(set(graph.incoming(n1)), set())
        self.assertEqual(set(graph.edges()), {(n1, n2, 63)})

    def test_finding(self):
        graph = modulegraph2.ObjectGraph()

        n1_a = Node("n1")
        n1_b = Node("n1")

        self.assertIsNot(n1_a, n1_b)

        graph.add_node(n1_a)

        self.assertTrue(n1_a in graph)
        self.assertTrue(n1_b in graph)

        v = graph.find_node("n1")
        self.assertIs(v, n1_a)

        v = graph.find_node(n1_a)
        self.assertIs(v, n1_a)

        v = graph.find_node(n1_b)
        self.assertIs(v, n1_a)

    def test_duplicate_node(self):
        graph = modulegraph2.ObjectGraph()

        n1_a = Node("n1")
        n1_b = Node("n1")

        graph.add_node(n1_a)
        self.assertRaises(ValueError, graph.add_node, n1_b)
        self.assertRaises(AttributeError, graph.add_node, "n2")

    def test_edges(self):
        graph = modulegraph2.ObjectGraph()

        n1 = Node("n1")
        n2 = Node("n2")
        n3 = Node("n3")
        n4 = Node("n4")

        graph.add_node(n1)
        graph.add_node(n2)
        graph.add_node(n3)

        graph.add_edge(n1, n2, 1)
        graph.add_edge("n1", "n3", 2)
        graph.add_edge("n2", n3, None)

        self.assertRaises(KeyError, graph.add_edge, n1, n4, 3)
        self.assertRaises(KeyError, graph.add_edge, n4, n2, 4)
        self.assertRaises(KeyError, graph.add_edge, "n1", "n4", 3)
        self.assertRaises(KeyError, graph.add_edge, "n4", "n3", 5)

        self.assertEqual(graph.edge_data(n1, n2), 1)
        self.assertEqual(graph.edge_data(n1, n3), 2)
        self.assertEqual(graph.edge_data(n2, n3), None)

        self.assertEqual(graph.edge_data(n1, "n2"), 1)
        self.assertEqual(graph.edge_data(n1, "n3"), 2)
        self.assertEqual(graph.edge_data(n2, "n3"), None)

        self.assertEqual(graph.edge_data("n1", n2), 1)
        self.assertEqual(graph.edge_data("n1", n3), 2)
        self.assertEqual(graph.edge_data("n2", n3), None)

        self.assertEqual(graph.edge_data("n1", "n2"), 1)
        self.assertEqual(graph.edge_data("n1", "n3"), 2)
        self.assertEqual(graph.edge_data("n2", "n3"), None)

        self.assertRaises(KeyError, graph.edge_data, "n1", "n4")
        self.assertRaises(KeyError, graph.edge_data, n1, n4)
        self.assertRaises(KeyError, graph.edge_data, "n4", "n2")
        self.assertRaises(KeyError, graph.edge_data, n4, n2)
        self.assertRaises(KeyError, graph.edge_data, "n3", "n1")
        self.assertRaises(KeyError, graph.edge_data, n3, n1)

        self.assertEqual(set(graph.outgoing(n1)), {(1, n2), (2, n3)})
        self.assertEqual(set(graph.outgoing(n2)), {(None, n3)})

        self.assertEqual(set(graph.incoming(n1)), set())
        self.assertEqual(set(graph.incoming(n2)), {(1, n1)})
        self.assertEqual(set(graph.incoming(n3)), {(2, n1), (None, n2)})

    def test_graph_iteration(self):
        graph = modulegraph2.ObjectGraph()

        n1 = Node("n1")
        n2 = Node("n2")
        n3 = Node("n3")
        n4 = Node("n4")
        n5 = Node("n5")
        n6 = Node("n6")
        n7 = Node("n7")
        n8 = Node("n8")

        graph.add_node(n1)
        graph.add_node(n2)
        graph.add_node(n3)
        graph.add_node(n4)
        graph.add_node(n5)
        graph.add_node(n6)
        graph.add_node(n7)

        graph.add_root(n1)
        graph.add_root(n2)

        graph.add_edge(n1, n3, None)
        graph.add_edge(n3, n1, None)
        graph.add_edge(n3, n4, None)
        graph.add_edge(n3, n5, None)
        graph.add_edge(n5, n4, None)
        graph.add_edge(n5, n1, None)

        graph.add_edge(n2, n6, None)
        graph.add_edge(n6, n7, None)
        graph.add_edge(n7, n6, None)

        self.assertEqual(list(graph.iter_graph(node=n2)), [n2, n6, n7])
        self.assertEqual(list(graph.iter_graph(node=n7)), [n7, n6])
        self.assertIn(
            list(graph.iter_graph(node=n1)), ([n1, n3, n4, n5], [n1, n3, n5, n4])
        )

        with self.assertRaises(KeyError):
            list(graph.iter_graph(node=n8))

        self.assertEqual(set(graph.iter_graph()), {n1, n2, n3, n4, n5, n6, n7})

        graph.add_edge(n1, n2, None)
        self.assertEqual(set(graph.iter_graph()), {n1, n2, n3, n4, n5, n6, n7})
