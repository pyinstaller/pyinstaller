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
# Tests for pkgutil.iter_modules(). The test attempts to list contents of a package in both unfrozen and frozen version,
# and compares the obtained lists.
#
# We test three scenarios; a pure-python top-level package (using json package from stdlib), a pure-python sub-package
# (using xml.dom package from stdlib), and a package with binary extensions (using psutil).
#
# The extensions are present on filesystem as-is, and are therefore handled by python's FileFinder. The collected .pyc
# modules, however, are embedded in PYZ archive, and are not visible to standard python's finders/loaders. The exception
# to that is noarchive mode, where .pyc modules are not collected into archive; as they are present on filesystem as-is,
# they are again handled directly by python's FileFinder. Therefore, each test is performed both in archive and in
# noarchive mode, to cover both cases.

import os

import pytest

from PyInstaller.compat import exec_python_rc
from PyInstaller.utils.tests import importable

# Directory with testing modules used in some tests.
_MODULES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modules')


# Read the output file produced by test script. Each line consists of two elements separated by semi-colon:
# name;ispackage
def _read_results_file(filename):
    output = []
    with open(filename, 'r', encoding='utf-8') as fp:
        for line in fp:
            tokens = line.split(';')
            assert len(tokens) == 2
            output.append((tokens[0], int(tokens[1])))
    # Sort the results, so we can compare them
    return sorted(output)


@pytest.mark.parametrize(
    'package',
    [
        'json',  # pure python package (stdlib)
        'xml.dom',  # sub-package (stdlib)
        'psutil',  # package with extensions (3rd party)
    ]
)
@pytest.mark.parametrize('archive', ['archive', 'noarchive'])
def test_pkgutil_iter_modules(package, script_dir, tmpdir, pyi_builder, archive, resolve_pkg_path=False):
    # Ensure package is available
    if not importable(package.split(".")[0]):
        pytest.skip("Needs " + package)

    # Full path to test script
    test_script = 'pyi_pkgutil_iter_modules.py'
    test_script = os.path.join(script_dir, test_script)

    # Run unfrozen test script
    out_unfrozen = os.path.join(tmpdir, 'output-unfrozen.txt')
    rc = exec_python_rc(test_script, package, '--output-file', out_unfrozen)
    assert rc == 0
    # Read results
    results_unfrozen = _read_results_file(out_unfrozen)

    # Run frozen script
    out_frozen = os.path.join(tmpdir, 'output-frozen.txt')
    debug_args = ['--debug', 'noarchive'] if archive == 'noarchive' else []
    pyi_builder.test_script(
        test_script,
        pyi_args=[
            # ensure everything is collected
            '--collect-submodules', package,
            # enable/disable noarchive
            *debug_args,
        ],
        app_args=[package, '--output-file', out_frozen] + (['--resolve-pkg-path'] if resolve_pkg_path else [])
    )  # yapf: disable
    # Read results
    results_frozen = _read_results_file(out_frozen)

    # Compare
    assert results_unfrozen == results_frozen


# Repeat test_pkgutil_iter_modules() test with package path resolving enabled. In this mode, the test script fully
# resolves the package path before passing it to pkgutil.iter_modules(), reproducing the scenario of #6537 on macOS:
# the temporary directory used by onefile builds is placed in /var, which is symbolic link to /private/var. Therefore,
# the resolved package path (/private/var/...) in the frozen application may differ from non-resolved one (/var/...),
# and our pkgutil.iter_modules() therefore needs to explicitly resolve the given paths and the sys._MEIPASS prefix to
# ensure proper matching.
# The test is applicable only to macOS in onefile mode.
@pytest.mark.darwin
def test_pkgutil_iter_modules_resolve_pkg_path(script_dir, tmpdir, pyi_builder):
    if pyi_builder._mode != 'onefile':
        pytest.skip('The test is applicable only to onefile mode.')
    # A single combination (altgraph package, archive mode) is enough to check for proper symlink handling.
    test_pkgutil_iter_modules('json', script_dir, tmpdir, pyi_builder, archive=True, resolve_pkg_path=True)


# Additional test for macOS .app bundles and packages that contain data files. See #7884. In generated .app bundles,
# _MEIPASS points to `Contents/Frameworks`, while the data files are collected into `Contents/Resources` directory. If
# a package contains only data files, the whole package directory is collected into `Contents/Resources`, and a symbolic
# link to package's directory is made in `Contents/Frameworks`. Our `pkgutil.iter_modules` implementation needs to
# account for this when validating the package path prefix; i.e., that attempting to resolve
# `Contents/Frameworks/mypackage` will result in `Contents/Resource/mypackage` due to symbolic link, and thus the prefix
# will not directly match _MEIPASS anymore.
#
# This issue affects packages with only data files; if the package has no data or binary files, then the package
# directory does not exist on filesystem and the resolution attempt leaves it unchanged. If the package contains both
# data and binary files, the directory is created in both Contents/Frameworks and Contents/Resources, and the contents
# are cross-linked between them on file level.
@pytest.mark.darwin
def test_pkgutil_iter_modules_macos_app_bundle(script_dir, tmpdir, pyi_builder, monkeypatch):
    if pyi_builder._mode != 'onedir':
        pytest.skip('The test is applicable only to onedir mode.')

    pathex = os.path.join(_MODULES_DIR, 'pyi_pkgutil_itermodules', 'package')
    hooks_dir = os.path.join(_MODULES_DIR, 'pyi_pkgutil_itermodules', 'hooks')
    package = 'mypackage'

    # Full path to test script
    test_script = 'pyi_pkgutil_iter_modules.py'
    test_script = os.path.join(script_dir, test_script)

    # Run unfrozen test script
    env = os.environ.copy()
    if 'PYTHONPATH' in env:
        pathex = os.pathsep.join([pathex, env['PYTHONPATH']])
    env['PYTHONPATH'] = pathex
    out_unfrozen = os.path.join(tmpdir, 'output-unfrozen.txt')
    rc = exec_python_rc(test_script, package, '--output-file', out_unfrozen, env=env)
    assert rc == 0
    # Read results
    results_unfrozen = _read_results_file(out_unfrozen)

    # Freeze the test program
    # This also runs both executables (POSIX build and .app bundle) with same arguments, so we have no way of separating
    # the output file. Therefore, we will manually re-run the executables ourselves.
    pyi_builder.test_script(
        test_script,
        pyi_args=[
            '--paths', pathex,
            '--hiddenimport', package,
            '--additional-hooks-dir', hooks_dir,
            '--windowed',  # enable .app bundle
        ],
        app_args=[package],
    )  # yapf: disable

    # Run each executable and verify its output
    executables = pyi_builder._find_executables('pyi_pkgutil_iter_modules')
    assert executables
    for idx, exe in enumerate(executables):
        out_frozen = os.path.join(tmpdir, f"output-frozen-{idx}.txt")
        rc = pyi_builder._run_executable(
            exe,
            args=[package, '--output-file', out_frozen],
            run_from_path=False,
            runtime=None,
        )
        assert rc == 0
        results_frozen = _read_results_file(out_frozen)
        print("RESULTS", results_frozen, "\n\n")

        assert results_unfrozen == results_frozen


# Two tests that reproduce the situation from #8191. In the first test, `pkgutil.iter_modules()` is called on a path
# that corresponds to a module instead of the package. In the second test, we add a sub-directory component to the path
# that corresponds to a module. Both cases should be handled gracefully by our `iter_modules` override.
def test_pkgutil_iter_modules_with_module_path(pyi_builder):
    pyi_builder.test_source(
        """
        import os
        import pkgutil
        import json.encoder  # Our test module

        # Path to iterate over; sys._MEIPASS/json/encoder
        search_path, _ = os.path.splitext(json.encoder.__file__)

        # pkgutil.iter_modules()
        print("Search path:", search_path)
        entries = list(pkgutil.iter_modules([search_path]))
        print("Entries:", entries)
        assert len(entries) == 0, "Expected no entries!"
        """
    )


def test_pkgutil_iter_modules_with_module_path_subdir(pyi_builder):
    pyi_builder.test_source(
        """
        import os
        import pkgutil
        import json.encoder  # Our test module

        # Path to iterate over; sys._MEIPASS/json/encoder/nonexistent
        search_path, _ = os.path.splitext(json.encoder.__file__)
        search_path = os.path.join(search_path, 'nonexistent')

        # pkgutil.iter_modules()
        print("Search path:", search_path)
        entries = list(pkgutil.iter_modules([search_path]))
        print("Entries:", entries)
        assert len(entries) == 0, "Expected no entries!"
        """
    )
