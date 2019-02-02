import unittest
import unittest.mock
import contextlib
import io
import os
import sys
import io
import argparse
import pathlib
import tempfile
import shutil

from modulegraph2 import __main__ as main

import modulegraph2

from . import util


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


class TestPrinter(unittest.TestCase):
    # XXX: This currently is nothing more than a smoke test,
    # the output format is not validated in any way.

    @classmethod
    def tearDownClass(cls):
        util.clear_sys_modules(
            pathlib.Path(pathlib.Path(__file__).resolve().parent / "modulegraph-dir")
        )

    def setUp(self):
        self.mg = modulegraph2.ModuleGraph()
        self.mg.add_module("os")
        self.mg.add_module("faulthandler")
        self.mg.add_distribution("wheel")

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

    def test_dot_graph_with_structure(self):
        fp = io.StringIO()

        self.mg.add_script(
            pathlib.Path(__file__).resolve().parent
            / "modulegraph-dir"
            / "trivial-script"
        )

        with main.saved_sys_path():
            sys.path.insert(
                0,
                os.fspath(pathlib.Path(__file__).resolve().parent / "modulegraph-dir"),
            )

            self.mg.add_module("global_import")
            self.mg.add_module("missing_in_package")
            self.mg.add_module("import_sys_star")
            self.mg.add_module("wheel")
            self.mg.add_module("wheel.__main__")
            self.mg.add_module("pip")

        main.print_graph(fp, main.OutputFormat.GRAPHVIZ, self.mg)

        text = fp.getvalue()
        self.assertTrue(text.startswith("digraph modulegraph {"))


class TestBuilder(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        util.clear_sys_modules(
            pathlib.Path(pathlib.Path(__file__).resolve().parent / "modulegraph-dir")
        )

    def test_graph_modules(self):
        args = argparse.Namespace()
        args.node_type = main.NodeType.MODULE
        args.path = [
            os.fspath(pathlib.Path(__file__).resolve().parent / "modulegraph-dir")
        ]
        args.excludes = ["no_imports", "circular_c"]
        args.name = ["global_import", "circular_a"]

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
        args.path = [
            os.fspath(pathlib.Path(__file__).resolve().parent / "modulegraph-dir")
        ]
        args.excludes = ["no_imports"]
        args.name = []

        mg = main.make_graph(args)

        self.assertEqual(list(mg.nodes()), [])

    def test_graph_script(self):
        args = argparse.Namespace()
        args.node_type = main.NodeType.SCRIPT
        args.path = [
            os.fspath(pathlib.Path(__file__).resolve().parent / "modulegraph-dir")
        ]
        args.excludes = []
        args.name = [
            os.fspath(
                pathlib.Path(__file__).resolve().parent
                / "modulegraph-dir"
                / "trivial-script"
            )
        ]

        mg = main.make_graph(args)
        roots = list(mg.roots())

        self.assertEqual(len(roots), 1)
        self.assertTrue(isinstance(roots[0], modulegraph2.Script))

    def test_graph_scripts(self):
        args = argparse.Namespace()
        args.node_type = main.NodeType.SCRIPT
        args.path = [
            os.fspath(pathlib.Path(__file__).resolve().parent / "modulegraph-dir")
        ]
        args.excludes = []
        args.name = [
            os.fspath(
                pathlib.Path(__file__).resolve().parent
                / "modulegraph-dir"
                / "trivial-script"
            )
        ] * 2

        mg = main.make_graph(args)
        roots = list(mg.roots())

        self.assertEqual(len(roots), 1)
        self.assertTrue(isinstance(roots[0], modulegraph2.Script))

    def test_graph_scripts(self):
        args = argparse.Namespace()
        args.node_type = main.NodeType.SCRIPT
        args.path = [
            os.fspath(pathlib.Path(__file__).resolve().parent / "modulegraph-dir")
        ]
        args.excludes = []
        args.name = []

        mg = main.make_graph(args)
        self.assertEqual(list(mg.nodes()), [])

    def test_graph_distribution(self):
        args = argparse.Namespace()
        args.node_type = main.NodeType.DISTRIBUTION
        args.path = []
        args.excludes = []
        args.name = ["wheel"]

        mg = main.make_graph(args)
        roots = list(mg.roots())

        self.assertEqual(len(roots), 1)
        self.assertTrue(isinstance(roots[0], modulegraph2.PyPIDistribution))

    def test_graph_no_distribution(self):
        args = argparse.Namespace()
        args.node_type = main.NodeType.DISTRIBUTION
        args.path = []
        args.excludes = []
        args.name = []

        mg = main.make_graph(args)
        self.assertEqual(list(mg.nodes()), [])


class TestFormatGraph(unittest.TestCase):
    @unittest.mock.patch("modulegraph2.__main__.print_graph", spec=True)
    def test_format_to_stdout(self, print_graph):
        args = argparse.Namespace()
        args.output_file = None
        args.output_format = main.OutputFormat.HTML

        mg = modulegraph2.ModuleGraph()

        rv = main.format_graph(args, mg)
        self.assertIs(rv, None)

        print_graph.assert_called_once_with(sys.stdout, args.output_format, mg)

    @unittest.mock.patch("modulegraph2.__main__.print_graph", spec=True)
    def test_format_to_file(self, print_graph):
        td = tempfile.mkdtemp()

        try:
            args = argparse.Namespace()
            args.output_file = os.path.join(td, "filename.dot")
            args.output_format = main.OutputFormat.GRAPHVIZ

            mg = modulegraph2.ModuleGraph()

            rv = main.format_graph(args, mg)
            self.assertIs(rv, None)

            print_graph.assert_called_once()
            self.assertTrue(
                isinstance(print_graph.mock_calls[-1][1][0], io.TextIOWrapper)
            )
            self.assertEqual(print_graph.mock_calls[-1][1][0].name, args.output_file)

            self.assertEqual(print_graph.mock_calls[-1][1][1], args.output_format)

            self.assertIs(print_graph.mock_calls[-1][1][2], mg)

        finally:
            os.unlink(os.path.join(td, "filename.dot"))
            os.rmdir(td)

    def test_format_to_invalid_file(self):
        with captured_output() as (stdout, stderr):
            args = argparse.Namespace()
            args.output_file = os.path.join("nosuchdir/filename.dot")
            args.output_format = main.OutputFormat.GRAPHVIZ

            mg = modulegraph2.ModuleGraph()

            self.assertRaises(SystemExit, main.format_graph, args, mg)

        self.assertIn("No such file or directory", stderr.getvalue())


class TestMain(unittest.TestCase):
    @unittest.mock.patch("modulegraph2.__main__.parse_arguments", spec=True)
    @unittest.mock.patch("modulegraph2.__main__.make_graph", spec=True)
    @unittest.mock.patch("modulegraph2.__main__.format_graph", spec=True)
    def test_main_order(self, format_graph, make_graph, parse_arguments):
        # This is way to specific and is not much better than code that
        # ensures we can have 100% test coverage.
        argv = unittest.mock.MagicMock()
        parse_arguments.return_value = unittest.mock.MagicMock()
        make_graph.return_value = unittest.mock.MagicMock()

        result = main.main(argv)

        self.assertIs(result, None)
        parse_arguments.assert_called_once_with(argv)
        make_graph.assert_called_once_with(parse_arguments.return_value)
        format_graph.assert_called_once_with(
            parse_arguments.return_value, make_graph.return_value
        )
