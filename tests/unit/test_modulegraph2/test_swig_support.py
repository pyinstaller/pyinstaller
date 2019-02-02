import unittest
import pathlib
import os
import importlib.util
import sys
import contextlib
import subprocess
import shutil

import modulegraph2

from . import util

INPUT_DIR = pathlib.Path(__file__).resolve().parent / "swig-dir"


@contextlib.contextmanager
def prefixed_sys_path(dir_path):
    sys.path.insert(0, os.fspath(dir_path))
    try:
        yield

    finally:
        assert sys.path[0] == os.fspath(dir_path)
        del sys.path[0]


class TestSWIGSupport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for subdir in INPUT_DIR.iterdir():
            if not subdir.is_dir():
                continue

            if not (subdir / "setup.py").exists():
                continue

            if (subdir / "build").exists():
                shutil.rmtree(subdir / "build")
            if (subdir / "dist").exists():
                shutil.rmtree(subdir / "dist")
            subprocess.check_call(
                [sys.executable, "setup.py", "build_ext"],
                cwd=subdir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    @classmethod
    def tearDownClass(cls):
        util.clear_sys_modules(INPUT_DIR)

        for subdir in INPUT_DIR.iterdir():
            if not subdir.is_dir():
                continue

            if (subdir / "build").exists():
                shutil.rmtree(subdir / "build")
            if (subdir / "dist").exists():
                shutil.rmtree(subdir / "dist")

    def tearDown(self):
        util.clear_sys_modules(INPUT_DIR)

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

    def assert_has_node(self, mg, node, node_type=None):
        value = mg.find_node(node)
        self.assertIsNot(value, None)
        if node_type is not None:
            self.assertTrue(isinstance(value, node_type))

    def test_toplevel(self):
        with prefixed_sys_path(INPUT_DIR / "toplevel"):

            mg = modulegraph2.ModuleGraph()
            mg.add_module("example")

            self.assert_has_node(mg, "example", modulegraph2.SourceModule)
            self.assert_has_node(mg, "_example", modulegraph2.ExtensionModule)

            self.assert_has_edge(mg, "example", "_example", None)

    def test_toplevel_without_hook(self):
        with prefixed_sys_path(INPUT_DIR / "toplevel"):

            mg = modulegraph2.ModuleGraph(use_builtin_hooks=False)
            mg.add_module("example")

            self.assert_has_node(mg, "example", modulegraph2.SourceModule)
            self.assert_has_node(mg, "_example", modulegraph2.ExtensionModule)

            self.assert_has_edge(mg, "example", "_example", None)

    def test_package_init(self):
        with prefixed_sys_path(INPUT_DIR / "package"):

            mg = modulegraph2.ModuleGraph()
            mg.add_module("using")

            self.assert_has_node(mg, "using", modulegraph2.SourceModule)
            self.assert_has_node(mg, "example", modulegraph2.Package)

            # Note that this is a toplevel module, not in the package:
            self.assert_has_node(mg, "_example", modulegraph2.ExtensionModule)

            self.assert_has_edge(mg, "example", "_example", None)

    def test_package_init_without_hook(self):
        with prefixed_sys_path(INPUT_DIR / "package"):

            mg = modulegraph2.ModuleGraph(use_builtin_hooks=False)
            mg.add_module("using")

            self.assert_has_node(mg, "using", modulegraph2.SourceModule)
            self.assert_has_node(mg, "example", modulegraph2.Package)

            # Note that this is a toplevel module, not in the package:
            self.assert_has_node(mg, "_example", modulegraph2.MissingModule)

            self.assert_has_edge(mg, "example", "_example", None)

    def test_package_submod(self):
        with prefixed_sys_path(INPUT_DIR / "package_submod"):

            mg = modulegraph2.ModuleGraph()
            mg.add_module("using")

            self.assert_has_node(mg, "using", modulegraph2.SourceModule)
            self.assert_has_node(mg, "package", modulegraph2.Package)
            self.assert_has_node(mg, "package.example", modulegraph2.SourceModule)

            # Note that this is a toplevel module, not in the package:
            self.assert_has_node(mg, "_example", modulegraph2.ExtensionModule)

            self.assert_has_edge(mg, "package.example", "_example", None)

    def test_package_submod_without_hook(self):
        with prefixed_sys_path(INPUT_DIR / "package_submod"):

            mg = modulegraph2.ModuleGraph(use_builtin_hooks=False)
            mg.add_module("using")

            self.assert_has_node(mg, "using", modulegraph2.SourceModule)
            self.assert_has_node(mg, "package", modulegraph2.Package)
            self.assert_has_node(mg, "package.example", modulegraph2.SourceModule)

            # Note that this is a toplevel module, not in the package:
            self.assert_has_node(mg, "_example", modulegraph2.MissingModule)

            self.assert_has_edge(mg, "package.example", "_example", None)

    def test_missing_but_not_swig(self):
        with prefixed_sys_path(INPUT_DIR / "not_swig"):

            mg = modulegraph2.ModuleGraph()
            mg.add_module("example")

            self.assert_has_node(mg, "example", modulegraph2.SourceModule)

            # Note that this is a toplevel module, not in the package:
            self.assert_has_node(mg, "_example", modulegraph2.MissingModule)

            self.assert_has_edge(mg, "example", "_example", None)

    def test_package_extension_not_found(self):
        with prefixed_sys_path(INPUT_DIR / "package_no_ext"):

            mg = modulegraph2.ModuleGraph()
            mg.add_module("using")

            self.assert_has_node(mg, "using", modulegraph2.SourceModule)
            self.assert_has_node(mg, "package", modulegraph2.Package)
            self.assert_has_node(mg, "package.example", modulegraph2.SourceModule)

            # Note that this is a toplevel module, not in the package:
            self.assert_has_node(mg, "_example", modulegraph2.MissingModule)

            self.assert_has_edge(mg, "package.example", "_example", None)

    def test_package_extension_is_module(self):
        with prefixed_sys_path(INPUT_DIR / "package_toplevel_module"):

            mg = modulegraph2.ModuleGraph()
            mg.add_module("using")

            self.assert_has_node(mg, "using", modulegraph2.SourceModule)
            self.assert_has_node(mg, "package", modulegraph2.Package)
            self.assert_has_node(mg, "package.example", modulegraph2.SourceModule)

            # Note that this is a toplevel module, not in the package:
            self.assert_has_node(mg, "_example", modulegraph2.MissingModule)

            self.assert_has_edge(mg, "package.example", "_example", None)
