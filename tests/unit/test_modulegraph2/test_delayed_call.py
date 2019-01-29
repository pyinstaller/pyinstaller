import unittest

from modulegraph2 import _delayed_call as delayed_call
from modulegraph2 import _nodes as nodes


class TestDelayedCaller(unittest.TestCase):
    def test_empty(self):
        node = nodes.MissingModule("nosuchmodule")
        proc = delayed_call.DelayedCaller()
        self.assertFalse(proc.have_finished_work())
        self.assertEqual(repr(proc), "<DelayedCaller #finished_q=0 #waiting=0>")
        self.assertFalse(proc.has_unfinished)
        proc.finished(node)
        self.assertEqual(repr(proc), "<DelayedCaller #finished_q=1 #waiting=0>")
        self.assertTrue(proc.has_unfinished)
        self.assertTrue(proc.have_finished_work())
        proc.process_finished_nodes()
        self.assertEqual(repr(proc), "<DelayedCaller #finished_q=0 #waiting=0>")
        self.assertFalse(proc.has_unfinished)
        self.assertFalse(proc.have_finished_work())

    def test_basic(self):
        node1 = nodes.MissingModule("node1")
        node2 = nodes.MissingModule("node2")

        proc = delayed_call.DelayedCaller()

        results = []
        proc.wait_for(node1, node2, lambda n1, n2: results.append((n1, n2)))
        self.assertTrue(proc.has_unfinished)
        self.assertEqual(repr(proc), "<DelayedCaller #finished_q=0 #waiting=1>")
        self.assertEqual(results, [])
        self.assertFalse(proc.have_finished_work())

        self.assertFalse(proc.is_finished(node1))
        proc.finished(node1)
        self.assertTrue(proc.have_finished_work())
        proc.process_finished_nodes()
        self.assertTrue(proc.is_finished(node1))
        proc.process_finished_nodes()
        self.assertEqual(results, [])

        self.assertFalse(proc.is_finished(node2))
        proc.finished(node2)
        proc.process_finished_nodes()
        self.assertTrue(proc.is_finished(node2))
        self.assertEqual(results, [(node1, node2)])

        del results[:]

        node3 = nodes.MissingModule("node3")

        proc.wait_for(node3, node2, lambda n1, n2: results.append((n1, n2)))
        self.assertEqual(results, [])
        proc.process_finished_nodes()
        self.assertEqual(results, [(node3, node2)])

        self.assertFalse(proc.is_finished(node3))
        self.assertFalse(proc.have_finished_work())

    def test_multi_wait(self):
        node1 = nodes.MissingModule("node1")
        node2 = nodes.MissingModule("node2")

        proc = delayed_call.DelayedCaller()

        results = []
        proc.wait_for(
            node1, node2, lambda n1, n2: results.append((n1.identifier, n2.identifier))
        )
        proc.wait_for(
            node1,
            node2,
            lambda n1, n2: results.append(
                (n1.identifier.upper(), n2.identifier.upper())
            ),
        )

        proc.finished(node2)
        self.assertEqual(results, [])
        proc.process_finished_nodes()
        self.assertEqual(results, [("node1", "node2"), ("NODE1", "NODE2")])
        self.assertFalse(proc.have_finished_work())
