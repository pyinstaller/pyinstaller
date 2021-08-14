#-----------------------------------------------------------------------------
# Copyright (c) 2005-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
#
# These tests run a test script (scripts/pyi_pkg_resources_provider.py) in unfrozen and frozen form, in combination with
# a custom test package (modules/pyi_pkg_resources_provider/package) in either source or zipped egg form.
#
# Running the unfrozen test script allows us to verify the behavior of DefaultProvider and ZipProvider from
# pkg_resources and thereby also validate the test script itself. Running the frozen test validates the behavior of the
# PyiFrozenProvider.
#
# For details on the structure of the test and the contents of the test package, see the top comment in the test script
# itself.

import os
import shutil

import pytest

from PyInstaller.utils.tests import importorskip
from PyInstaller.compat import exec_python, exec_python_rc

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


@importorskip('pkg_resources')
@pytest.mark.parametrize('package_type', ['pkg', 'egg'])
def test_pkg_resources_provider_source(package_type, tmpdir, script_dir, monkeypatch):
    # Run the test script unfrozen - to validate it is working and to verify the behavior of
    # pkg_resources.DefaultProvider / ZipProvider.
    pathex = __get_test_package_path(package_type, tmpdir, monkeypatch)
    test_script = 'pyi_pkg_resources_provider.py'
    test_script = os.path.join(
        str(script_dir),  # not is_py36: str()
        test_script
    )
    ret = __exec_python_script(test_script, pathex=pathex)
    assert ret == 0, "Test script failed!"


@importorskip('pkg_resources')
@pytest.mark.parametrize('package_type', ['pkg', 'egg'])
def test_pkg_resources_provider_frozen(pyi_builder, package_type, tmpdir, script_dir, monkeypatch):
    # Run the test script as a frozen program
    pathex = __get_test_package_path(package_type, tmpdir, monkeypatch)
    test_script = 'pyi_pkg_resources_provider.py'
    hooks_dir = os.path.join(_MODULES_DIR, 'pyi_pkg_resources_provider', 'hooks')
    pyi_builder.test_script(
        test_script,
        pyi_args=['--paths', pathex, '--hidden-import', 'pyi_pkgres_testpkg', '--additional-hooks-dir', hooks_dir]
    )
