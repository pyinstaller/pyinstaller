import unittest
import os
import pathlib
import shutil
import subprocess
import sys
import importlib

import modulegraph2
from modulegraph2 import _graphbuilder as graphbuilder

from . import util

INPUT_DIR = pathlib.Path(__file__).resolve().parent / "six-dir"


class TestSixSupport(unittest.TestCase, util.TestMixin):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, os.fspath(INPUT_DIR))

        site_dir = INPUT_DIR / "site-packages"
        sys.path.insert(0, os.fspath(site_dir))

        if site_dir.exists():
            shutil.rmtree(site_dir)

        site_dir.mkdir()

        subprocess.check_call(
            [
                sys.executable,
                "-mpip",
                "-qqq",
                "install",
                "--target",
                os.fspath(site_dir),
                "six",
            ]
        )

        # This is a fairly crude hack to ensure that
        # "six.moves.winreg" is present, even on systems
        # that aren't win32.
        #
        # The failed relocation is needed in one of the
        # tests.
        try:
            orig_platform = sys.platform
            sys.platform = "win32"
            import six
        finally:
            six.platform = orig_platform

    @classmethod
    def tearDownClass(cls):
        util.clear_sys_modules(INPUT_DIR)

        assert sys.path[0] == os.fspath(INPUT_DIR / "site-packages")
        del sys.path[0]

        assert sys.path[0] == os.fspath(INPUT_DIR)
        del sys.path[0]

        shutil.rmtree(INPUT_DIR / "site-packages")

    def test_six(self):
        mg = modulegraph2.ModuleGraph()
        mg.add_module("using_six")

        self.assert_has_node(mg, "using_six", modulegraph2.SourceModule)
        self.assert_has_node(mg, "six", modulegraph2.SourceModule)
        self.assert_has_node(mg, "six.moves", modulegraph2.Package)
        self.assert_has_node(mg, "six.moves.html_parser", modulegraph2.AliasNode)
        self.assert_has_node(mg, "six.moves.urllib.error", modulegraph2.AliasNode)
        self.assert_has_node(mg, "html", modulegraph2.Package)
        self.assert_has_node(mg, "html.parser", modulegraph2.SourceModule)
        self.assert_has_node(mg, "importlib", modulegraph2.Package)
        self.assert_has_node(mg, "functools", modulegraph2.SourceModule)
        self.assert_has_node(mg, "urllib.error", modulegraph2.SourceModule)

        self.assert_has_edge(
            mg,
            "using_six",
            "six.moves",
            {modulegraph2.DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "using_six",
            "six.moves.html_parser",
            {modulegraph2.DependencyInfo(False, True, True, None)},
        )
        self.assert_has_edge(
            mg,
            "using_six",
            "six.moves.urllib.error",
            {modulegraph2.DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "using_six",
            "functools",  # six.moves.reduce
            {modulegraph2.DependencyInfo(False, True, False, None)},
        )

        self.assert_has_edge(
            mg,
            "six.moves.html_parser",
            "html.parser",
            {modulegraph2.DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "using_six",
            "importlib",  # six.moves.reload_module
            {modulegraph2.DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "six.moves.urllib.error",
            "urllib.error",
            {modulegraph2.DependencyInfo(False, True, False, None)},
        )

        self.assertRaises(
            KeyError, mg.edge_data, "using_six", "six.moves.reload_module"
        )

        node = mg.find_node("six.moves")
        self.assertFalse(node.has_data_files)

    def test_six_incorrect(self):
        try:
            moved_copyreg = graphbuilder.SIX_MOVES_TO.pop("copyreg")

            mg = modulegraph2.ModuleGraph()
            mg.add_module("using_six_incorrectly")

            self.assert_has_node(mg, "using_six_incorrectly", modulegraph2.SourceModule)
            self.assert_has_node(mg, "six", modulegraph2.SourceModule)
            self.assert_has_node(mg, "six.moves", modulegraph2.Package)
            self.assert_has_node(mg, "six.moves.copyreg", modulegraph2.MissingModule)

            self.assert_has_edge(
                mg,
                "using_six_incorrectly",
                "six.moves",
                {modulegraph2.DependencyInfo(False, True, False, None)},
            )
            self.assert_has_edge(
                mg,
                "using_six_incorrectly",
                "six.moves.copyreg",
                {modulegraph2.DependencyInfo(False, True, True, None)},
            )

        finally:
            graphbuilder.SIX_MOVES_TO["copyreg"] = moved_copyreg

    @unittest.skipIf(sys.platform == "win32", "Test will pass on win32")
    def test_moved_to_missing(self):
        mg = modulegraph2.ModuleGraph()
        mg.add_module("using_six_moved_to_missing")

        self.assert_has_node(
            mg, "using_six_moved_to_missing", modulegraph2.SourceModule
        )
        self.assert_has_node(mg, "six", modulegraph2.SourceModule)
        self.assert_has_node(mg, "six.moves", modulegraph2.Package)
        self.assert_has_node(mg, "six.moves.winreg", modulegraph2.AliasNode)
        self.assert_has_node(mg, "winreg", modulegraph2.MissingModule)

        self.assert_has_edge(
            mg,
            "using_six_moved_to_missing",
            "six.moves",
            {modulegraph2.DependencyInfo(False, True, False, None)},
        )
        self.assert_has_edge(
            mg,
            "using_six_moved_to_missing",
            "six.moves.winreg",
            {modulegraph2.DependencyInfo(False, True, True, None)},
        )
        self.assert_has_edge(
            mg,
            "six.moves.winreg",
            "winreg",
            {modulegraph2.DependencyInfo(False, True, False, None)},
        )

    def test_vendored_six(self):
        # Same as test_six, but now with six installed as sub package,
        # as used by a number of projects that have vendored six.
        return

        (INPUT_DIR / "site-packages" / "vendored").mkdir()
        with open(INPUT_DIR / "site-packages" / "vendored" / "__init__.py", "w") as fp:
            fp.write("''' init '''\n")

        (INPUT_DIR / "site-packages" / "six").rename(
            INPUT_DIR / "site-packages" / "vendored" / "six"
        )

        try:
            mg = modulegraph2.ModuleGraph()
            mg.add_module("using_vendored_six")

            self.assert_has_node(mg, "using_six", modulegraph2.SourceModule)
            self.assert_has_node(mg, "vendored.six", modulegraph2.SourceModule)
            self.assert_has_node(
                mg, "vendored.six.moves", modulegraph2.NamespacePackage
            )
            self.assert_has_node(
                mg, "vendored.six.moves.html_parser", modulegraph2.AliasNode
            )
            self.assertRaises(
                KeyError, mg.edge_data, "using_six", "vendored.six.moves.reload_module"
            )
            self.assert_has_node(
                mg, "vendored.six.moves.urllib.error", modulegraph2.AliasNode
            )
            self.assertRaises(
                KeyError, mg.edge_data, "using_six", "vendored.six.moves.reduce"
            )
            self.assert_has_node(mg, "html.parser", modulegraph2.Package)
            self.assert_has_node(mg, "importlib", modulegraph2.Package)
            self.assert_has_node(mg, "urllib.error", modulegraph2.Package)

            self.assert_has_edge(
                mg,
                "using_six",
                "vendored.six.moves",
                {modulegraph2.DependencyInfo(False, True, True, None)},
            )
            self.assert_has_edge(
                mg,
                "using_six",
                "vendored.six.moves.html_parser",
                {modulegraph2.DependencyInfo(False, True, True, None)},
            )
            self.assert_has_edge(
                mg,
                "using_six",
                "vendored.six.moves.reload_module",
                {modulegraph2.DependencyInfo(False, True, True, None)},
            )
            self.assert_has_edge(
                mg,
                "using_six",
                "vendored.six.moves.urllib.error",
                {modulegraph2.DependencyInfo(False, True, True, None)},
            )
            self.assert_has_edge(
                mg,
                "using_six",
                "vendored.six.moves.reduce",
                {modulegraph2.DependencyInfo(False, True, True, None)},
            )

            self.assert_has_edge(
                mg,
                "vendored.six.moves.html_parser",
                "html.parser",
                {modulegraph2.DependencyInfo(False, True, False, None)},
            )
            self.assert_has_edge(
                mg,
                "vendored.six.moves.reload_module",
                "importlib",
                {modulegraph2.DependencyInfo(False, True, False, None)},
            )
            self.assert_has_edge(
                mg,
                "vendored.six.moves.urllib.error",
                "urllib.error",
                {modulegraph2.DependencyInfo(False, True, False, None)},
            )
            self.assert_has_edge(
                mg,
                "vendored.six.moves.reduce",
                "functools",
                {modulegraph2.DependencyInfo(False, True, False, None)},
            )

        finally:
            (INPUT_DIR / "site-packages" / "vendored" / "six").rename(
                INPUT_DIR / "site-packages" / "six"
            )
