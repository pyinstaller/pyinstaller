#-----------------------------------------------------------------------------
# Copyright (c) 2021, PyInstaller Development Team.
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
# We test two packages; altgraph (pure-python) and psutil (contains binary extensions). The extensions are present on
# filesystem as-is, and are therefore handled by python's FileFinder. The collected .pyc modules, however, are embedded
# in PYZ archive, and are not visible to standard python's finders/loaders. The exception to that is noarchive mode,
# where .pyc modules are not collected into archive; as they are present on filesystem as-is, they are again handled
# directly by python's FileFinder. Therefore, the test is performed both in archive and in noarchive mode, to cover both
# cases.

import os

import pytest

from PyInstaller.compat import exec_python_rc
from PyInstaller.utils.tests import importable


# Read the output file produced by test script. Each line consists of two elements separated by semi-colon:
# name;ispackage
def _read_results_file(filename):
    output = []
    with open(filename, 'r') as fp:
        for line in fp:
            tokens = line.split(';')
            assert len(tokens) == 2
            output.append((tokens[0], int(tokens[1])))
    # Sort the results, so we can compare them
    return sorted(output)


@pytest.mark.parametrize(
    'package',
    [
        'altgraph',  # pure python package
        'psutil',  # package with extensions
        'psutil.tests',  # sub-package
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
            # however, psutil.tests pulls in pip and wheel, which in turn manage to pull in pyinstaller.exe/__main__ and
            # break Windows noarchive build. So exclude those explicitly.
            '--exclude', 'pip',
            '--exclude', 'wheel',
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
    test_pkgutil_iter_modules('altgraph', script_dir, tmpdir, pyi_builder, archive=True, resolve_pkg_path=True)
