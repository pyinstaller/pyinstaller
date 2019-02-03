import unittest
import shutil
import os
import pathlib
import importlib.machinery
import subprocess
import sys
import pathlib

try:
    import importlib.resources as resources
except ImportError:
    import importlib_resources as resources

from modulegraph2 import _graphbuilder as graphbuilder
from modulegraph2 import (
    BuiltinModule,
    BytecodeModule,
    ExtensionModule,
    FrozenModule,
    NamespacePackage,
    Package,
    PyPIDistribution,
    SourceModule,
    MissingModule,
)

from . import util

NODEBUILDER_TREE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "nodebuilder-tree"
)


class TestContainsData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        util.clear_sys_modules(NODEBUILDER_TREE)

    @classmethod
    def tearDownClass(cls):
        util.clear_sys_modules(NODEBUILDER_TREE)

    def setUp(self):
        subprocess.check_call(
            [sys.executable, "setup.py", "build_zipfile"], cwd=NODEBUILDER_TREE
        )

        sys.path.insert(0, os.path.join(NODEBUILDER_TREE, "packages.zip"))
        sys.path.insert(0, NODEBUILDER_TREE)

    def tearDown(self):
        assert sys.path[0] == NODEBUILDER_TREE
        del sys.path[0]

        assert sys.path[0] == os.path.join(NODEBUILDER_TREE, "packages.zip")
        del sys.path[0]

        os.unlink(os.path.join(NODEBUILDER_TREE, "packages.zip"))

    def test_importlib(self):
        self.assertTrue(resources.is_resource("datapackage2.subdir", "data.txt"))
        self.assertTrue(resources.is_resource("zfdatapackage", "data.txt"))

    def test_graphbuilder(self):
        self.assertFalse(
            graphbuilder._contains_datafiles(
                pathlib.Path(NODEBUILDER_TREE) / "datapackage1"
            )
        )
        self.assertTrue(
            graphbuilder._contains_datafiles(
                pathlib.Path(NODEBUILDER_TREE) / "datapackage2"
            )
        )
        self.assertTrue(
            graphbuilder._contains_datafiles(
                pathlib.Path(NODEBUILDER_TREE) / "bytecode_package"
            )
        )
        self.assertTrue(
            graphbuilder._contains_datafiles(
                pathlib.Path(NODEBUILDER_TREE) / "packages.zip" / "zfdatapackage"
            )
        )
        self.assertFalse(
            graphbuilder._contains_datafiles(
                pathlib.Path(NODEBUILDER_TREE) / "packages.zip" / "zfpackage"
            )
        )

    def test_invalid(self):
        self.assertRaises(
            os.error, graphbuilder._contains_datafiles, pathlib.Path("/no/such/file")
        )
        self.assertRaises(
            os.error,
            graphbuilder._contains_datafiles,
            pathlib.Path(NODEBUILDER_TREE) / "extension1.c" / "package",
        )


class TestNodeBuilder(unittest.TestCase):
    @classmethod
    def _remove_artefacts(cls):
        for dname, dirs, files in os.walk(NODEBUILDER_TREE):
            to_remove = []
            for d in dirs:
                if d in {"build", "dist", "__pycache__"}:
                    shutil.rmtree(os.path.join(dname, d))
                    to_remove.append(d)
            for d in to_remove:
                dirs.remove(d)

            for fn in files:
                if any(
                    fn.endswith(sfx)
                    for sfx in importlib.machinery.BYTECODE_SUFFIXES
                    + importlib.machinery.EXTENSION_SUFFIXES
                    + [".zip"]
                ):
                    os.unlink(os.path.join(dname, fn))

    @classmethod
    def setUpClass(cls):
        cls._remove_artefacts()

        subprocess.check_call(
            [
                sys.executable,
                "setup.py",
                "build_ext",
                "build_bytecode",
                "build_zipfile",
            ],
            cwd=NODEBUILDER_TREE,
        )

        sys.path.insert(0, os.path.join(NODEBUILDER_TREE, "packages.zip"))
        sys.path.insert(0, NODEBUILDER_TREE)

    @classmethod
    def tearDownClass(cls):
        cls._remove_artefacts()

        assert sys.path[0] == NODEBUILDER_TREE
        del sys.path[0]

        assert sys.path[0] == os.path.join(NODEBUILDER_TREE, "packages.zip")
        del sys.path[0]

        util.clear_sys_modules(NODEBUILDER_TREE)

    def test_builtin_module(self):
        spec = importlib.util.find_spec("sys")

        node, imports = graphbuilder.node_for_spec(spec, sys.path)

        self.assertIsInstance(node, BuiltinModule)
        self.assertEqual(node.name, "sys")
        self.assertEqual(node.identifier, "sys")

        self.assertIsNot(node.loader, None)
        self.assertIs(node.distribution, None)
        self.assertIs(node.filename, None)

        self.assertEqual(node.extension_attributes, {})
        self.assertEqual(node.globals_written, set())
        self.assertEqual(node.globals_read, set())

    def test_frozen(self):
        spec = importlib.util.find_spec("_frozen_importlib")

        node, imports = graphbuilder.node_for_spec(spec, sys.path)

        self.assertIsInstance(node, FrozenModule)
        self.assertEqual(node.name, "_frozen_importlib")
        self.assertEqual(node.identifier, "_frozen_importlib")

        self.assertIsNot(node.loader, None)
        self.assertIs(node.distribution, None)
        self.assertIs(node.filename, None)

        self.assertEqual(node.extension_attributes, {})

    def test_source_module(self):
        spec = importlib.util.find_spec("simple_source")

        node, imports = graphbuilder.node_for_spec(spec, sys.path)

        self.assertIsInstance(node, SourceModule)
        self.assertEqual(node.name, "simple_source")
        self.assertEqual(node.identifier, "simple_source")

        self.assertIsNot(node.loader, None)
        self.assertIs(node.distribution, None)
        self.assertEqual(
            node.filename, pathlib.Path(NODEBUILDER_TREE) / "simple_source.py"
        )

        self.assertEqual(node.extension_attributes, {})
        self.assertEqual(node.globals_written, {"foo", "bar", "sys", "__doc__"})
        self.assertEqual(node.globals_read, {"foo"})

    def test_bytecode_module(self):
        # Module with only a PYC file
        spec = importlib.util.find_spec("bytecode_module")

        node, imports = graphbuilder.node_for_spec(spec, sys.path)

        self.assertIsInstance(node, BytecodeModule)
        self.assertEqual(node.name, "bytecode_module")
        self.assertEqual(node.identifier, "bytecode_module")

        self.assertIsNot(node.loader, None)
        self.assertIs(node.distribution, None)
        self.assertEqual(
            node.filename, pathlib.Path(NODEBUILDER_TREE) / "bytecode_module.pyc"
        )

        self.assertEqual(node.extension_attributes, {})
        self.assertEqual(node.globals_written, {"os", "a", "b", "__doc__"})
        self.assertEqual(node.globals_read, {"a", "os", "len"})

    def test_extension_module(self):
        spec = importlib.util.find_spec("extension")

        node, imports = graphbuilder.node_for_spec(spec, sys.path)

        self.assertIsInstance(node, ExtensionModule)
        self.assertEqual(node.name, "extension")
        self.assertEqual(node.identifier, "extension")

        self.assertIsNot(node.loader, None)
        self.assertIs(node.distribution, None)
        self.assertEqual(
            node.filename,
            pathlib.Path(
                os.path.join(
                    NODEBUILDER_TREE,
                    "extension" + importlib.machinery.EXTENSION_SUFFIXES[0],
                )
            ),
        )

        self.assertEqual(node.extension_attributes, {})
        self.assertEqual(node.globals_written, set())
        self.assertEqual(node.globals_read, set())

    def test_implicit_namespace_package(self):
        spec = importlib.util.find_spec("namespace_package")

        node, imports = graphbuilder.node_for_spec(spec, sys.path)

        self.assertIsInstance(node, NamespacePackage)
        self.assertEqual(node.name, "namespace_package")
        self.assertEqual(node.identifier, "namespace_package")

        self.assertEqual(
            node.search_path, [pathlib.Path(NODEBUILDER_TREE) / "namespace_package"]
        )
        self.assertEqual(node.has_data_files, False)

    def test_package_empty_init(self):
        spec = importlib.util.find_spec("empty_init")

        node, imports = graphbuilder.node_for_spec(spec, sys.path)

        self.assertIsInstance(node, Package)
        self.assertEqual(node.name, "empty_init")
        self.assertEqual(node.identifier, "empty_init")

        self.assertEqual(
            node.search_path, [pathlib.Path(NODEBUILDER_TREE) / "empty_init"]
        )
        self.assertEqual(node.has_data_files, False)

        self.assertIsInstance(node.init_module, SourceModule)

    def test_package_init_source(self):
        # Package with __init__.py
        spec = importlib.util.find_spec("package")

        node, imports = graphbuilder.node_for_spec(spec, sys.path)

        self.assertIsInstance(node, Package)
        self.assertEqual(node.name, "package")
        self.assertEqual(node.identifier, "package")

        self.assertEqual(node.search_path, [pathlib.Path(NODEBUILDER_TREE) / "package"])
        self.assertEqual(node.has_data_files, False)

        self.assertIsInstance(node.init_module, SourceModule)

    def test_package_init_bytecode(self):
        # Package with __init__.pyc
        spec = importlib.util.find_spec("bytecode_package")

        node, imports = graphbuilder.node_for_spec(spec, sys.path)

        self.assertIsInstance(node, Package)
        self.assertEqual(node.name, "bytecode_package")
        self.assertEqual(node.identifier, "bytecode_package")

        self.assertEqual(
            node.search_path, [pathlib.Path(NODEBUILDER_TREE) / "bytecode_package"]
        )
        self.assertEqual(node.has_data_files, True)

        self.assertIsInstance(node.init_module, BytecodeModule)

    def test_package_init_extension(self):
        # Package with extension as __init__
        spec = importlib.util.find_spec("ext_package")

        node, imports = graphbuilder.node_for_spec(spec, sys.path)

        self.assertIsInstance(node, Package)
        self.assertEqual(node.name, "ext_package")
        self.assertEqual(node.identifier, "ext_package")

        self.assertEqual(
            node.search_path, [pathlib.Path(NODEBUILDER_TREE) / "ext_package"]
        )
        self.assertEqual(node.has_data_files, False)

        self.assertIsInstance(node.init_module, ExtensionModule)

    def test_distribution(self):
        spec = importlib.util.find_spec("pip")
        node, imports = graphbuilder.node_for_spec(spec, sys.path)
        self.assertIsInstance(node, Package)

        self.assertIsInstance(node.distribution, PyPIDistribution)
        self.assertEqual(node.distribution.name, "pip")

    def test_zipfile_module(self):
        spec = importlib.util.find_spec("zfmod")

        node, imports = graphbuilder.node_for_spec(spec, sys.path)

        self.assertIsInstance(node, SourceModule)
        self.assertEqual(node.name, "zfmod")
        self.assertEqual(node.identifier, "zfmod")

        self.assertIsNot(node.loader, None)
        self.assertIs(node.distribution, None)
        self.assertEqual(
            node.filename, pathlib.Path(NODEBUILDER_TREE) / "packages.zip" / "zfmod.py"
        )

        self.assertEqual(node.extension_attributes, {})
        self.assertEqual(node.globals_written, {"__doc__"})
        self.assertEqual(node.globals_read, set())

    def test_zipfile_package(self):
        spec = importlib.util.find_spec("zfpackage")

        node, imports = graphbuilder.node_for_spec(spec, sys.path)

        self.assertIsInstance(node, Package)
        self.assertEqual(node.name, "zfpackage")
        self.assertEqual(node.identifier, "zfpackage")

        self.assertEqual(
            node.search_path,
            [pathlib.Path(NODEBUILDER_TREE) / "packages.zip" / "zfpackage"],
        )
        self.assertEqual(node.has_data_files, False)

        self.assertIsInstance(node.init_module, SourceModule)

    def test_zipfile_data_package(self):
        spec = importlib.util.find_spec("zfdatapackage")

        node, imports = graphbuilder.node_for_spec(spec, sys.path)

        self.assertIsInstance(node, Package)
        self.assertEqual(node.name, "zfdatapackage")
        self.assertEqual(node.identifier, "zfdatapackage")

        self.assertEqual(
            node.search_path,
            [pathlib.Path(NODEBUILDER_TREE) / "packages.zip" / "zfdatapackage"],
        )
        self.assertEqual(node.has_data_files, True)

        self.assertIsInstance(node.init_module, SourceModule)

    def test_zipfile_implicit_namespace_package(self):
        spec = importlib.util.find_spec("zfnspackage")

        node, imports = graphbuilder.node_for_spec(spec, sys.path)

        self.assertIsInstance(node, NamespacePackage)
        self.assertEqual(node.name, "zfnspackage")
        self.assertEqual(node.identifier, "zfnspackage")

        self.assertEqual(
            node.search_path,
            [pathlib.Path(NODEBUILDER_TREE) / "packages.zip" / "zfnspackage"],
        )
        self.assertEqual(node.has_data_files, False)


class TestRelativePackage(unittest.TestCase):
    def test_relative_package_regular(self):
        self.assertEqual(graphbuilder.relative_package(MissingModule("foo"), 2), None)
        self.assertEqual(graphbuilder.relative_package(MissingModule("foo"), 1), None)

        self.assertEqual(
            graphbuilder.relative_package(MissingModule("foo.bar"), 1), "foo"
        )
        self.assertEqual(
            graphbuilder.relative_package(MissingModule("foo.bar"), 2), None
        )

        self.assertEqual(
            graphbuilder.relative_package(MissingModule("foo.bar.baz"), 1), "foo.bar"
        )
        self.assertEqual(
            graphbuilder.relative_package(MissingModule("foo.bar.baz"), 2), "foo"
        )

    def test_relative_package_package(self):
        p = Package("foo.bar", None, None, None, None, None, None, None, None)

        self.assertEqual(graphbuilder.relative_package(p, 1), "foo.bar")
        self.assertEqual(graphbuilder.relative_package(p, 2), "foo")
        self.assertEqual(graphbuilder.relative_package(p, 3), None)

    def test_relative_package_namespace_package(self):
        p = NamespacePackage("foo.bar", None, None, None, None, None, None)

        self.assertEqual(graphbuilder.relative_package(p, 1), "foo.bar")
        self.assertEqual(graphbuilder.relative_package(p, 2), "foo")
        self.assertEqual(graphbuilder.relative_package(p, 3), None)
