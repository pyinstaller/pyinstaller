from importlib.machinery import EXTENSION_SUFFIXES
import os
import tempfile
import shutil
import subprocess
import sys
import unittest
import zipfile

import modulegraph2._distributions as distributions
import modulegraph2


def rewrite_record(wheel_file):
    zf = zipfile.ZipFile(wheel_file, "a")
    if "simple_package-1.0.dist-info/RECORD" not in zf.namelist():
        zf.close()
        return

    record = zf.read("simple_package-1.0.dist-info/RECORD")

    new = []
    for ln in record.splitlines():
        fields = ln.rsplit(b",", 2)
        if fields[0].startswith(b'"'):
            continue

        if b'"' in fields[0]:
            fields[0] = fields[0].replace(b'"', b'""')
        if b"," in fields[0] or b'"' in fields[0]:
            fields[0] = b'"' + fields[0] + b'"'
        new.append(b",".join(fields) + b"\n")
    record = b"".join(new)
    zf.writestr("simple_package-1.0.dist-info/RECORD", record)
    zf.close()


def build_and_install(source_path, destination_path):
    for subdir in ("build", "dist"):
        if os.path.exists(os.path.join(source_path, subdir)):
            shutil.rmtree(os.path.join(source_path, subdir))

    subprocess.check_call([sys.executable, "setup.py", "bdist_wheel"], cwd=source_path)

    dist_dir = os.path.join(source_path, "dist")
    for fn in os.listdir(dist_dir):
        if fn.endswith(".whl"):
            wheel_file = os.path.join(dist_dir, fn)
            break
    else:
        raise RuntimeError("Wheel not build")

    # XXX: Wheel 0.32.3 generates a RECORD that is not a vallid CSV, and
    # pip doesn't like that. Therefore rewrite the RECORD file in one of
    # the test zipfiles.
    rewrite_record(wheel_file)

    subprocess.check_call(
        [sys.executable, "-mpip", "-qqq", "install", "-t", destination_path, wheel_file]
    )


class TestPackageBuilder(unittest.TestCase):
    def setUp(self):
        self._cached_distributions = distributions._cached_distributions.copy()
        distributions._cached_distributions.clear()

    def tearDown(self):
        distributions._cached_distributions.clear()
        distributions._cached_distributions.update(self._cached_distributions)

    def test_basic_package(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            build_and_install(
                os.path.join(os.path.dirname(__file__), "simple-package"), tmpdir
            )

            for fn in os.listdir(tmpdir):
                if fn.startswith("simple_package") and fn.endswith(".dist-info"):
                    info = distributions.create_distribution(os.path.join(tmpdir, fn))
                    break
            else:
                self.fail("Cannot find simple-package installation")

            self.assertEqual(info.name, "simple-package")
            self.assertEqual(info.version, "1.0")
            self.assertEqual(
                info.import_names,
                {"extension", "toplevel", "package", "package.module"},
            )

            PYC = f".{sys.implementation.cache_tag}.pyc"
            expected = {
                os.path.join(tmpdir, "extension" + EXTENSION_SUFFIXES[0]),
                os.path.join(tmpdir, "toplevel.py"),
                os.path.join(tmpdir, "__pycache__", "toplevel" + PYC),
                os.path.join(tmpdir, "package", "__init__.py"),
                os.path.join(tmpdir, "package", "__pycache__", "__init__" + PYC),
                os.path.join(tmpdir, "package", "module.py"),
                os.path.join(tmpdir, "package", "__pycache__", "module" + PYC),
                os.path.join(tmpdir, "package", "datafile.txt"),
                os.path.join(tmpdir, "package", "other,data.dat"),
                os.path.join(tmpdir, "simple_package-1.0.dist-info", "RECORD"),
                os.path.join(tmpdir, "simple_package-1.0.dist-info", "INSTALLER"),
                os.path.join(tmpdir, "simple_package-1.0.dist-info", "WHEEL"),
                os.path.join(tmpdir, "simple_package-1.0.dist-info", "METADATA"),
                os.path.join(tmpdir, "simple_package-1.0.dist-info", "top_level.txt"),
                os.path.join(tmpdir, "simple_package-1.0.dist-info", "direct_url.json"),
            }
            if sys.platform != "win32":
                expected.add(os.path.join(tmpdir, "package", 'my"data.txt'))
            self.assertEqual(info.files, expected)

            self.assertTrue(info.contains_file(os.path.join(tmpdir, "toplevel.py")))
            self.assertFalse(info.contains_file(os.path.join("toplevel.py")))

    def test_bytecode_package(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            build_and_install(
                os.path.join(os.path.dirname(__file__), "bytecode-package"), tmpdir
            )

            for fn in os.listdir(tmpdir):
                if fn.startswith("bytecode_package") and fn.endswith(".dist-info"):
                    info = distributions.create_distribution(os.path.join(tmpdir, fn))
                    break
            else:
                self.fail("Cannot find bytecode-package installation")

            self.assertEqual(info.name, "bytecode-package")
            self.assertEqual(info.version, "1.0")
            self.assertEqual(info.import_names, {"package", "package.module"})

            self.assertEqual(
                info.files,
                {
                    os.path.join(tmpdir, "package", "__init__.pyc"),
                    os.path.join(tmpdir, "package", "module.pyc"),
                    os.path.join(tmpdir, "bytecode_package-1.0.dist-info", "RECORD"),
                    os.path.join(tmpdir, "bytecode_package-1.0.dist-info", "INSTALLER"),
                    os.path.join(tmpdir, "bytecode_package-1.0.dist-info", "WHEEL"),
                    os.path.join(tmpdir, "bytecode_package-1.0.dist-info", "METADATA"),
                    os.path.join(
                        tmpdir, "bytecode_package-1.0.dist-info", "direct_url.json"
                    ),
                    os.path.join(
                        tmpdir, "bytecode_package-1.0.dist-info", "top_level.txt"
                    ),
                },
            )

            self.assertTrue(
                info.contains_file(os.path.join(tmpdir, "package", "module.pyc"))
            )
            self.assertFalse(info.contains_file(os.path.join("package", "module.pyc")))


class TestPackageFinder(unittest.TestCase):
    def test_not_found(self):
        self.assertEqual(
            distributions.distribution_for_file(os.path.abspath(__file__), sys.path),
            None,
        )

    def test_found_package(self):
        import pip

        p = distributions.distribution_for_file(os.path.abspath(pip.__file__), sys.path)
        self.assertEqual(p.name, "pip")


class TestPackageLister(unittest.TestCase):
    def setUp(self):
        self._cached_distributions = distributions._cached_distributions.copy()
        distributions._cached_distributions.clear()

    def tearDown(self):
        distributions._cached_distributions.clear()
        distributions._cached_distributions.update(self._cached_distributions)

    def test_all_distributions(self):
        seen = set()
        for dist in distributions.all_distributions(sys.path):
            self.assertTrue(isinstance(dist, distributions.PyPIDistribution))
            seen.add(dist.name)

        self.assertIn("pip", seen)
        self.assertIn("wheel", seen)

        seen2 = set()
        for dist in distributions.all_distributions(sys.path):
            self.assertTrue(isinstance(dist, distributions.PyPIDistribution))
            seen2.add(dist.name)

        self.assertEqual(seen, seen2)

    def test_distribution_named(self):
        dist = distributions.distribution_named("pip")
        self.assertIsNot(dist, None)
        self.assertTrue(isinstance(dist, distributions.PyPIDistribution))
        self.assertEqual(dist.name, "pip")

        dist = distributions.distribution_named("no-such-dist")
        self.assertIs(dist, None)
