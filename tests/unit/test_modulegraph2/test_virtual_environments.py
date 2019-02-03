import unittest

# - Create virtual environment (venv, virtualenv)
# - Install minimal stuff
# - Create graph with subprocess in the
#   virtual environment
# - Verify graph structure, primarily
#   check that stdlib nodes refer to stuff
#   in the global installation.
# - Expectation is that a lot of code can
#   be shared between tests.

import subprocess
import shutil
import sys
import os
import tempfile
import contextlib

if sys.platform == "win32":
    BIN_DIR = "Scripts"
else:
    BIN_DIR = "bin"


@contextlib.contextmanager
def temporary_directory():
    dirname = tempfile.mkdtemp()
    try:
        yield os.path.realpath(dirname)

    finally:
        shutil.rmtree(dirname)


def create_virtualenv(environment_module, workdir, name):
    if environment_module == "venv" and hasattr(sys, "real_prefix"):
        # For some reason venv doesn't install pip when run
        # from a virtualenv environment. Explicitly launch
        # global version
        subprocess.check_call(
            [
                os.path.join(sys.real_prefix, BIN_DIR, "python3"),
                "-m",
                environment_module,
                name,
            ],
            cwd=workdir,
        )

    else:
        subprocess.check_call(
            [sys.executable, "-m", environment_module, name], cwd=workdir
        )

    venv_dir = os.path.join(workdir, name)

    subprocess.check_call(
        [
            os.path.join(venv_dir, BIN_DIR, "python"),
            "-mpip",
            "install",
            "-qqq",
            "objectgraph",
        ]
    )
    if sys.version_info[:2] < (3, 7):
        subprocess.check_call(
            [
                os.path.join(venv_dir, BIN_DIR, "python"),
                "-mpip",
                "install",
                "-qqq",
                "dataclasses",
            ]
        )

    return venv_dir


def run_scriptlet(venv_dir):
    output = subprocess.check_output(
        [
            os.path.join(venv_dir, BIN_DIR, "python"),
            "-c",
            "import modulegraph2; mg = modulegraph2.ModuleGraph(); mg.add_module('pip'); mg.add_module('distutils'); mg.add_module('distutils.command.bdist'); mg.report()",
        ]
    )
    lines = output.decode("utf-8").splitlines()
    assert lines[2].startswith("-----")

    for ln in lines[3:]:
        yield ln.split(None, 2)[-1]


class TestVirtualEnv(unittest.TestCase):
    # virtualenv from PyPI
    environment_module = "virtualenv"

    def test_graph_in_virtual_env(self):
        with temporary_directory() as tmpdir:
            venv_dir = create_virtualenv(self.environment_module, tmpdir, "environ")

            for module_path in run_scriptlet(venv_dir):
                with self.subTest(module_path):
                    # Stdlib shoudl be outside the virtualenv, other modules should be inside
                    if "site-packages" in module_path:
                        self.assertTrue(
                            module_path.startswith(tmpdir),
                            f"{module_path!r} not in virtual environment {tmpdir!r}",
                        )

                    else:
                        self.assertFalse(
                            module_path.startswith(tmpdir),
                            f"{module_path!r} in virtual environment {tmpdir!r}",
                        )


class TestVenv(TestVirtualEnv):
    # venv from the stdlib
    environment_module = "venv"
