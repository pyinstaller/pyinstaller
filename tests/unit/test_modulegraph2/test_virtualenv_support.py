import unittest
import sys
import os
import pathlib

from modulegraph2 import _virtualenv_support as virtualenv_support
import modulegraph2

PYLIB_DIR = f"python{sys.version_info[0]}.{sys.version_info[1]}"

if hasattr(sys, "real_prefix"):

    class TestAdjustPath(unittest.TestCase):
        def test_stdlib(self):
            import token

            adjusted = virtualenv_support.adjust_path(token.__file__)
            self.assertEqual(
                adjusted, os.path.join(sys.real_prefix, "lib", PYLIB_DIR, "token.py")
            )

        def test_stdlib_extension(self):
            import cmath

            adjusted = virtualenv_support.adjust_path(cmath.__file__)
            self.assertEqual(
                adjusted,
                os.path.join(
                    sys.real_prefix,
                    "lib",
                    PYLIB_DIR,
                    "lib-dynload",
                    os.path.basename(cmath.__file__),
                ),
            )

        def test_distutils(self):
            import distutils

            adjusted = virtualenv_support.adjust_path(distutils.__file__)
            self.assertEqual(
                adjusted,
                os.path.join(
                    sys.real_prefix, "lib", PYLIB_DIR, "distutils", "__init__.py"
                ),
            )

            distutils_dir = os.path.dirname(distutils.__file__)
            adjusted = virtualenv_support.adjust_path(distutils_dir)
            self.assertEqual(
                adjusted, os.path.join(sys.real_prefix, "lib", PYLIB_DIR, "distutils")
            )

        def test_site(self):
            import site

            adjusted = virtualenv_support.adjust_path(site.__file__)
            self.assertEqual(
                adjusted, os.path.join(sys.real_prefix, "lib", PYLIB_DIR, "site.py")
            )

        def test_site_packages(self):
            import pip

            adjusted = virtualenv_support.adjust_path(pip.__file__)
            self.assertEqual(adjusted, pip.__file__)

        def test_other_path_in_env(self):
            self.assertEqual(
                virtualenv_support.adjust_path(sys.executable), sys.executable
            )

            path = os.path.join(sys.prefix, "lib", PYLIB_DIR, "foo.py")
            self.assertEqual(virtualenv_support.adjust_path(path), path)

        def test_system_path(self):
            path = "/etc"
            self.assertEqual(virtualenv_support.adjust_path(path), path)

    class TestAdjustUsage(unittest.TestCase):
        def test_adjustments(self):
            # Explicitly test adjustments for distutils because virtualenv environments
            # contain a stub distutils package that should not be present in the graph.
            mg = modulegraph2.ModuleGraph()
            mg.add_module("distutils.command.build_ext")

            node = mg.find_node("distutils")
            self.assertTrue(isinstance(node, modulegraph2.Package))
            self.assertTrue(isinstance(node.init_module, modulegraph2.SourceModule))

            self.assertEqual(
                node.init_module.filename,
                pathlib.Path(sys.real_prefix)
                / "lib"
                / PYLIB_DIR
                / "distutils"
                / "__init__.py",
            )
