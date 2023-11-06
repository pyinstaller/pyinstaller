#-----------------------------------------------------------------------------
# Copyright (c) 2021-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
#
# These tests run a test script (scripts/pyi_importlib_resources.py) in unfrozen and frozen form, in combination with
# a custom test package (modules/pyi_pkg_resources_provider/package). In contrast to test_pkg_resources_provider.py,
# only source package form is used (zipped egg form is nor tested).
#
# Running the unfrozen test script allows us to verify the behavior of importlib.resources (or its importlib_resources
# back-port for python 3.8 and earlier) and thereby also validate the test script itself. Running the frozen test
# validates the behavior of the resource reader implemented by PyInstaller's PyiFrozenImporter.
#
# For details on the structure of the test and the contents of the test package, see the top comment in the test script
# itself.

import os
import shutil

import pytest

from PyInstaller.utils.tests import skipif
from PyInstaller.compat import is_darwin, is_py39, exec_python, exec_python_rc
from PyInstaller.utils.hooks import check_requirement

# Directory with testing modules used in some tests.
_MODULES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modules')


def __exec_python_script(script_filename, pathex):
    # Prepare the environment - default to 'os.environ'...
    env = os.environ.copy()
    # ... and prepend PYTHONPATH with pathex
    if 'PYTHONPATH' in env:
        pathex = os.pathsep.join([pathex, env['PYTHONPATH']])
    env['PYTHONPATH'] = pathex
    # Run the test script
    return exec_python_rc(script_filename, env=env)


def __get_test_package_path(package_type, tmpdir, monkeypatch):
    # Same test package, in two different formats: source package or zipped egg (built on-the-fly)
    src_path = os.path.join(_MODULES_DIR, 'pyi_pkg_resources_provider', 'package')
    # Source package
    if package_type == 'pkg':
        return src_path
    # Copy files to a tmpdir for building the egg.
    dest_path = tmpdir.join('src')
    shutil.copytree(src_path, dest_path.strpath)
    monkeypatch.chdir(dest_path)
    # Create an egg from the test package. For debug, show the output of the egg build.
    print(exec_python('setup.py', 'bdist_egg'))
    # Obtain the name of the egg, which depends on the Python version.
    dist_path = dest_path.join('dist')
    files = os.listdir(dist_path.strpath)
    assert len(files) == 1
    egg_name = files[0]
    assert egg_name.endswith('.egg')
    # Return the full path to the egg file
    return dist_path.join(egg_name).strpath


@skipif(
    not is_py39 and not check_requirement('importlib_resources'),
    reason="Python prior to 3.9 requires importlib_resources."
)
@pytest.mark.parametrize('package_type', ['pkg'])  # Zipped egg ('egg') is not supported.
def test_importlib_resources_source(package_type, tmpdir, script_dir, monkeypatch):
    # Run the test script unfrozen - to validate it is working and to verify the behavior of importlib.resources
    # (or importlib_resources back-port).
    pathex = __get_test_package_path(package_type, tmpdir, monkeypatch)
    test_script = 'pyi_importlib_resources.py'
    test_script = os.path.join(
        str(script_dir),  # not is_py36: str()
        test_script
    )
    ret = __exec_python_script(test_script, pathex=pathex)
    assert ret == 0, "Test script failed!"


@skipif(
    not is_py39 and not check_requirement('importlib_resources'),
    reason="Python prior to 3.9 requires importlib_resources."
)
@pytest.mark.parametrize('package_type', ['pkg'])  # Zipped egg ('egg') is not supported.
def test_importlib_resources_frozen(pyi_builder, package_type, tmpdir, script_dir, monkeypatch):
    # Run the test script as a frozen program
    pathex = __get_test_package_path(package_type, tmpdir, monkeypatch)
    test_script = 'pyi_importlib_resources.py'
    hooks_dir = os.path.join(_MODULES_DIR, 'pyi_pkg_resources_provider', 'hooks')
    pyi_args = ['--paths', pathex, '--hidden-import', 'pyi_pkgres_testpkg', '--additional-hooks-dir', hooks_dir]
    if is_darwin:
        pyi_args += ['--windowed']  # Also build and test .app bundle executable
    pyi_builder.test_script(
        test_script,
        pyi_args=pyi_args,
    )


# A separate test for verifying that `importlib.resources.files()` works with PEP-420 namespace packages. See #7921.
# The sub-directory containing the data files is also a PEP-410 namespace (sub)package. However, in the context of
# PyInstaller, there are actually two slightly different possibilities:
#  - if we collect only the data files, and the namespace package itself is not collected into PYZ, the situation is
#    the same as in unfrozen python - python's built-in import machinery takes care of the namespace package and the
#    associated resource reader.
#  - if the namespace package is collected into PYZ (in addition to resources being collected as data files), the
#    namespace package ends up being handled by PyInstaller's `PyiFrozenImporter`, which requires extra care to ensure
#    compatibility with `importlib` resource reader.
# The test covers both scenarios via `as_package` parameter.
@skipif(
    not is_py39 and not check_requirement('importlib_resources'),
    reason="Python prior to 3.9 requires importlib_resources."
)
@pytest.mark.parametrize('as_package', [True, False])
def test_importlib_resources_namespace_package_data_files(pyi_builder, as_package):
    pathex = os.path.join(_MODULES_DIR, 'pyi_namespace_package_with_data', 'package')
    hooks_dir = os.path.join(_MODULES_DIR, 'pyi_namespace_package_with_data', 'hooks')
    if as_package:
        hidden_imports = ['--hidden-import', 'pyi_test_nspkg', '--hidden-import', 'pyi_test_nspkg.data']
    else:
        hidden_imports = ['--hidden-import', 'pyi_test_nspkg']
    pyi_args = ['--paths', pathex, *hidden_imports, '--additional-hooks-dir', hooks_dir]
    if is_darwin:
        pyi_args += ['--windowed']  # Also build and test .app bundle executable
    pyi_builder.test_source(
        """
        import importlib
        try:
            import importlib_resources
        except ModuleNotFoundError:
            import importlib.resources as importlib_resources

        # Get the package's directory (= our data directory)
        data_dir = importlib_resources.files("pyi_test_nspkg.data")

        # Sanity check; verify the directory's base name
        assert data_dir.name == "data"

        # Check that data files exist
        assert (data_dir / "data_file1.txt").is_file()
        assert (data_dir / "data_file2.txt").is_file()
        assert (data_dir / "data_file3.txt").is_file()

        # Force cache invalidation and check again.
        # This verifies that our `PyiFrozenImporter` correctly sets the `path_finder` argument when constructing
        # the `importlib._bootstrap_external._NamespacePath` for the namespace package. The `path_finder` is used
        # during refresh triggered by cache invalidation.
        importlib.invalidate_caches()

        data_dir = importlib_resources.files("pyi_test_nspkg.data")
        assert (data_dir / "data_file1.txt").is_file()
        """,
        pyi_args=pyi_args,
    )
