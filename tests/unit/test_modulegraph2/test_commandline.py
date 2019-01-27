import unittest
import contextlib
import io
import os
import sys
import io
import argparse
import pathlib

from modulegraph2 import __main__ as main

import modulegraph2

@contextlib.contextmanager
def captured_output():
    results = []

    _orig_stdout = sys.stdout
    _orig_stderr = sys.stderr

    try:
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()

        yield (sys.stdout, sys.stderr)

    finally:
        sys.stdout = _orig_stdout
        sys.stderr = _orig_stderr


class TestArguments(unittest.TestCase):
    def test_no_args(self):
        with captured_output() as (stdout, stderr):
            self.assertRaises(SystemExit, main.parse_arguments, [])

        self.assertIn(
            "error: the following arguments are required: name", stderr.getvalue()
        )

    def test_defaults(self):
        args = main.parse_arguments(["a", "b", "c"])

        self.assertEqual(args.name, ["a", "b", "c"])
        self.assertEqual(args.excludes, [])
        self.assertEqual(args.path, [])
        self.assertEqual(args.node_type, main.NodeType.MODULE)
        self.assertEqual(args.output_format, main.OutputFormat.HTML)
        self.assertEqual(args.output_file, None)

    def test_path(self):
        args = main.parse_arguments(["-p", "path1", "--path", "path2", "a"])
        self.assertEqual(args.path, ["path1", "path2"])

    def test_excludes(self):
        args = main.parse_arguments(["-x", "name1", "--exclude", "name2", "a"])
        self.assertEqual(args.excludes, ["name1", "name2"])

    def test_node_type(self):
        args = main.parse_arguments(["-s", "a"])
        self.assertEqual(args.node_type, main.NodeType.SCRIPT)

        args = main.parse_arguments(["--script", "a"])
        self.assertEqual(args.node_type, main.NodeType.SCRIPT)

        args = main.parse_arguments(["-m", "a"])
        self.assertEqual(args.node_type, main.NodeType.MODULE)

        args = main.parse_arguments(["--module", "a"])
        self.assertEqual(args.node_type, main.NodeType.MODULE)

        args = main.parse_arguments(["-d", "a"])
        self.assertEqual(args.node_type, main.NodeType.DISTRIBUTION)

        args = main.parse_arguments(["--distribution", "a"])
        self.assertEqual(args.node_type, main.NodeType.DISTRIBUTION)

    def test_output_format(self):
        args = main.parse_arguments(["--format", "html", "a"])
        self.assertEqual(args.output_format, main.OutputFormat.HTML)

        args = main.parse_arguments(["-f", "html", "a"])
        self.assertEqual(args.output_format, main.OutputFormat.HTML)

        args = main.parse_arguments(["--format", "dot", "a"])
        self.assertEqual(args.output_format, main.OutputFormat.GRAPHVIZ)

        args = main.parse_arguments(["-f", "dot", "a"])
        self.assertEqual(args.output_format, main.OutputFormat.GRAPHVIZ)

        with captured_output() as (stdout, stderr):
            self.assertRaises(SystemExit, main.parse_arguments, ["-f", "noformat", "a"])

        self.assertIn(
            "error: argument -f/--format: invalid choice: 'noformat' (choose from 'html', 'dot')",
            stderr.getvalue(),
        )

    def test_output_path(self):
        args = main.parse_arguments(["--output", "filename", "a"])
        self.assertEqual(args.output_file, "filename")

        args = main.parse_arguments(["-o", "filename", "a"])
        self.assertEqual(args.output_file, "filename")

    def test_help(self):
        with captured_output() as (stdout, stderr):
            self.assertRaises(SystemExit, main.parse_arguments, ["--help"])

        self.assertIn("positional arguments", stdout.getvalue())

class TestPathSaver (unittest.TestCase):
    def setUp(self):
        self.orig_path = sys.path[:]

    def tearDown(self):
        sys.path[:] = self.orig_path

    def test_no_action(self):
        with main.saved_syspath():
            pass

        self.assertEqual(sys.path, self.orig_path)

    def test_change_path(self):
        with main.saved_syspath():
            sys.path.insert(0, "foo")
            sys.path.insert(0, "bar")

        self.assertEqual(sys.path, self.orig_path)

class TestPrinter(unittest.TestCase):
    def setUp(self):
        self.mg = modulegraph2.ModuleGraph()
        self.mg.add_module('sys')

    def test_html_graph(self):
        fp = io.StringIO()

        main.print_graph(fp, main.OutputFormat.HTML, self.mg)

        text = fp.getvalue()
        self.assertTrue(text.startswith("<HTML>"))

    def test_dot_graph(self):
        fp = io.StringIO()

        main.print_graph(fp, main.OutputFormat.GRAPHVIZ, self.mg)

        text = fp.getvalue()
        self.assertTrue(text.startswith("digraph modulegraph {"))

class TestBuilder (unittest.TestCase):

    def test_graph_modules(self):
        args = argparse.Namespace()
        args.node_type = main.NodeType.MODULE
        args.path = [os.fspath(pathlib.Path(__file__).resolve().parent / "modulegraph-dir")]
        args.excludes = ["no_imports", "circular_c"]
        args.name = ["global_import", "circular_a" ]

        mg = main.make_graph(args)

        node = mg.find_node("global_import")
        self.assertTrue(isinstance(node, modulegraph2.SourceModule))

        node = mg.find_node("circular_a")
        self.assertTrue(isinstance(node, modulegraph2.SourceModule))

        node = mg.find_node("no_imports")
        self.assertTrue(isinstance(node, modulegraph2.ExcludedModule))

        node = mg.find_node("circular_c")
        self.assertTrue(isinstance(node, modulegraph2.ExcludedModule))

    def test_graph_no_modules(self):
        args = argparse.Namespace()
        args.node_type = main.NodeType.MODULE
        args.path = [os.fspath(pathlib.Path(__file__).resolve().parent / "modulegraph-dir")]
        args.excludes = ["no_imports"]
        args.name = []

        mg = main.make_graph(args)

        self.assertEqual(list(mg.nodes()), [])

    def test_graph_script(self):
        args = argparse.Namespace()
        args.node_type = main.NodeType.SCRIPT
        args.path = [os.fspath(pathlib.Path(__file__).resolve().parent / "modulegraph-dir")]
        args.excludes = []
        args.name = [ os.fspath(pathlib.Path(__file__).resolve().parent / "modulegraph-dir" / "trivial-script") ]

        mg = main.make_graph(args)
        roots = list(mg.roots())

        self.assertEqual(len(roots), 1)
        self.assertTrue(isinstance(roots[0], modulegraph2.Script))

    def test_graph_scripts(self):
        args = argparse.Namespace()
        args.node_type = main.NodeType.SCRIPT
        args.path = [os.fspath(pathlib.Path(__file__).resolve().parent / "modulegraph-dir")]
        args.excludes = []
        args.name = [ os.fspath(pathlib.Path(__file__).resolve().parent / "modulegraph-dir" / "trivial-script")] * 2

        mg = main.make_graph(args)
        roots = list(mg.roots())

        self.assertEqual(len(roots), 1)
        self.assertTrue(isinstance(roots[0], modulegraph2.Script))

    def test_graph_scripts(self):
        args = argparse.Namespace()
        args.node_type = main.NodeType.SCRIPT
        args.path = [os.fspath(pathlib.Path(__file__).resolve().parent / "modulegraph-dir")]
        args.excludes = []
        args.name = [ ]

        mg = main.make_graph(args)
        self.assertEqual(list(mg.nodes()), [])

    @unittest.skip("Distribution support is not yet implemented")
    def test_graph_distribution(self):
        args = argparse.Namespace()
        args.node_type = main.NodeType.DISTRIBUTION
        args.path = []
        args.excludes = []
        args.name = [ "pip" ]

        mg = main.make_graph(args)
        roots = list(mg.roots())

        self.assertEqual(len(roots), 1)
        self.assertTrue(isinstance(roots[0], modulegraph2.PyPIDistribution))

    @unittest.skip("Distribution support is not yet implemented")
    def test_graph_no_distribution(self):
        args = argparse.Namespace()
        args.node_type = main.NodeType.DISTRIBUTION
        args.path = [ ]
        args.excludes = []
        args.name = [ ]

        mg = main.make_graph(args)
        self.assertEqual(list(mg.nodes()), [])

class TestFormatGraph(unittest.TestCase):
    def test_missing(self):
        # Mock main.print_graph
        self.fail()

class TestMain(unittest.TestCase):
    def test_missing(self):
        # Just make sure the various functions are called in the right order
        # Use mocks.
        self.fail()
