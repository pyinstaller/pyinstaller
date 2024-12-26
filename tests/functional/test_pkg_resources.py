#-----------------------------------------------------------------------------
# Copyright (c) 2005-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import os
import pathlib

from PyInstaller.utils.tests import importorskip
from PyInstaller.compat import is_darwin, exec_python_rc

# Directory with testing modules used in some tests.
_MODULES_DIR = pathlib.Path(__file__).parent / 'modules'

# All tests in this file require pkg_resources
pytestmark = importorskip('pkg_resources')


def test_pkg_resources_importable(pyi_builder):
    """
    Check that a trivial example using pkg_resources does build.
    """
    pyi_builder.test_source("""
        import pkg_resources
        pkg_resources.working_set.require()
        """)


# Tests for pkg_resources provider.
#
# These tests run a test script (scripts/pyi_pkg_resources_provider.py) in unfrozen and frozen form, in combination with
# a custom test package (modules/pyi_pkg_resources_provider/package).
#
# Running the unfrozen test script allows us to verify the behavior of DefaultProvider from pkg_resources and thereby
# also validate the test script itself. Running the frozen test validates the behavior of the PyiFrozenProvider.
#
# For details on the structure of the test and the contents of the test package, see the top comment in the test script
# itself.
def _exec_python_script(script_filename, pathex):
    # Prepare the environment - default to 'os.environ'...
    env = os.environ.copy()
    # ... and prepend PYTHONPATH with pathex
    if 'PYTHONPATH' in env:
        pathex = os.pathsep.join([str(pathex), env['PYTHONPATH']])
    env['PYTHONPATH'] = str(pathex)
    # Run the test script
    return exec_python_rc(str(script_filename), env=env)


def test_pkg_resources_provider_source(tmp_path, script_dir, monkeypatch):
    # Run the test script unfrozen - to validate it is working and to verify the behavior of
    # pkg_resources.DefaultProvider.
    pathex = _MODULES_DIR / 'pyi_pkg_resources_provider' / 'package'
    test_script = script_dir / 'pyi_pkg_resources_provider.py'
    ret = _exec_python_script(test_script, pathex=pathex)
    assert ret == 0, "Test script failed!"


def test_pkg_resources_provider_frozen(pyi_builder, tmp_path, script_dir, monkeypatch):
    # Run the test script as a frozen program
    pathex = _MODULES_DIR / 'pyi_pkg_resources_provider' / 'package'
    test_script = 'pyi_pkg_resources_provider.py'
    hooks_dir = _MODULES_DIR / 'pyi_pkg_resources_provider' / 'hooks'
    pyi_args = [
        '--paths', str(pathex),
        '--hidden-import', 'pyi_pkgres_testpkg',
        '--additional-hooks-dir', str(hooks_dir),
    ]  # yapf: disable
    if is_darwin:
        pyi_args += ['--windowed']  # Also build and test .app bundle executable
    pyi_builder.test_script(
        test_script,
        pyi_args=pyi_args,
    )
