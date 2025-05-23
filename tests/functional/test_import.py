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

import pytest

from PyInstaller.compat import is_darwin
from PyInstaller.utils.tests import importorskip, xfail

# Directory with testing modules used in some tests.
_MODULES_DIR = pathlib.Path(__file__).parent / 'modules'


# Test that PyiFrozenLoader.get_source() works as expected when source .py file is available.
def test_loader_get_source(pyi_builder):
    pyi_builder.test_source(
        """
        import pyi_dummy_module
        from pyimod02_importers import PyiFrozenLoader

        # Ensure the module is handled by PyiFrozenLoader.
        loader = pyi_dummy_module.__loader__
        assert isinstance(loader, PyiFrozenLoader)

        # Check that loader.get_source() returns source from the .py file.
        assert loader.get_source('pyi_dummy_module') is not None
        """,
        pyi_args=[
            '--add-data',
            f'{_MODULES_DIR / "pyi_dummy_module.py"}:.',
        ]
    )


def test_nameclash(pyi_builder):
    # test-case for issue #964: Nameclashes in module information gathering All pyinstaller specific module attributes
    # should be prefixed, to avoid nameclashes.
    pyi_builder.test_source("""
        import pyi_testmod_nameclash.nameclash
        """)


def test_relative_import(pyi_builder):
    pyi_builder.test_source(
        """
        import pyi_testmod_relimp.B.C
        from pyi_testmod_relimp.F import H
        import pyi_testmod_relimp.relimp1

        assert pyi_testmod_relimp.relimp1.name == 'pyi_testmod_relimp.relimp1'
        assert pyi_testmod_relimp.B.C.name == 'pyi_testmod_relimp.B.C'
        assert pyi_testmod_relimp.F.H.name == 'pyi_testmod_relimp.F.H'
        """
    )


def test_relative_import2(pyi_builder):
    pyi_builder.test_source(
        """
        import pyi_testmod_relimp2.bar
        import pyi_testmod_relimp2.bar.bar2

        pyi_testmod_relimp2.bar.say_hello_please()
        pyi_testmod_relimp2.bar.bar2.say_hello_please()
        """
    )


def test_relative_import3(pyi_builder):
    pyi_builder.test_source(
        """
        from pyi_testmod_relimp3a.aa import a1
        print(a1.getString())
        """
    )


@xfail(reason='modulegraph bug')
def test_import_missing_submodule(pyi_builder):
    # If a submodule is missing, the parent submodule must be imported.
    pyi_builder.test_source(
        """
        try:
            import pyi_testmod_missing_submod.aaa.bbb
        except ImportError as e:
            assert e.message.endswith(' bbb')
        else:
            raise RuntimeError('Buggy test-case: module pyi_testmod_missing_submod.aaa.bbb must not exist')
        # parent module exists and must be included
        __import__('pyi_testmod_missing_submod.aaa')
        """
    )


def test_import_submodule_global_shadowed(pyi_builder):
    """
    Functional test validating issue #1919.

    `ModuleGraph` previously ignored `from`-style imports of submodules from packages whose `__init__` submodules
    declared global variables of the same name as those submodules. This test exercises this sporadic edge case by
    unsuccessfully importing a submodule "shadowed" by a global variable of the same name defined by their package's
    `__init__` submodule.
    """

    pyi_builder.test_source(
        """
        # Assert that this submodule is shadowed by a string global variable.
        from pyi_testmod_submodule_global_shadowed import submodule
        assert type(submodule) == str

        # Assert that this submodule is still frozen into this test application.
        # To do so:
        #
        # 1. Delete this global variable from its parent package.
        # 2. Assert that this submodule is unshadowed by this global variable.
        import pyi_testmod_submodule_global_shadowed, sys
        del  pyi_testmod_submodule_global_shadowed.submodule
        from pyi_testmod_submodule_global_shadowed import submodule
        assert type(submodule) == type(sys)
        """
    )


def test_import_submodule_global_unshadowed(pyi_builder):
    """
    Functional test validating issue #1919.

    `ModuleGraph` previously ignored `from`-style imports of submodules from packages whose `__init__` submodules
    declared global variables of the same name as those submodules. This test exercises this sporadic edge case by
    successfully importing a submodule:

    * Initially "shadowed" by a global variable of the same name defined by their package's `__init__` submodule.
    * Subsequently "unshadowed" when this global variable is then undefined by their package's `__init__` submodule.
    """

    pyi_builder.test_source(
        """
        # Assert that this submodule is unshadowed by this global variable.
        import sys
        from pyi_testmod_submodule_global_unshadowed import submodule
        assert type(submodule) == type(sys)
        """
    )


def test_import_submodule_from_aliased_pkg(pyi_builder, script_dir):
    pyi_builder.test_source(
        """
        import sys
        import pyi_testmod_submodule_from_aliased_pkg

        sys.modules['alias_name'] = pyi_testmod_submodule_from_aliased_pkg

        from alias_name import submodule
        """, ['--additional-hooks-dir', f"{script_dir / 'pyi_hooks'}"]
    )


def test_module_with_coding_utf8(pyi_builder):
    # Module ``utf8_encoded_module`` simply has an ``coding`` header and uses same German umlauts.
    pyi_builder.test_source("import module_with_coding_utf8")


# Test that our PyiFrozenLoader's get_source() method can load source files with utf-8 emoji characters.
# See issue #6143.
def test_source_utf8_emoji(pyi_builder):
    # Collect the module's source as data file
    add_data_arg = f"{_MODULES_DIR / 'module_with_utf8_emoji.py'}:."
    pyi_builder.test_source(
        """
        import inspect

        import module_with_utf8_emoji

        # Retrieve source code
        source = inspect.getsource(module_with_utf8_emoji)
        """, ['--add-data', add_data_arg]
    )


def test_hiddenimport(pyi_builder):
    # The script simply does nothing, not even print out a line. The check is done by comparing with
    # logs/test_hiddenimport.toc
    pyi_builder.test_source('pass', ['--hidden-import=a_hidden_import'])


def test_error_during_import(pyi_builder):
    # See ticket #27: historically, PyInstaller was catching all errors during imports...
    pyi_builder.test_source(
        """
        try:
            import error_during_import2
        except KeyError:
            print("OK")
        else:
            raise RuntimeError("failure!")
        """
    )


def test_import_non_existing_raises_import_error(pyi_builder):
    pyi_builder.test_source(
        """
        try:
            import zzzzzz.zzzzzzzz.zzzzzzz.non.existing.module.error_during_import2
        except ImportError:
            print("OK")
        else:
            raise RuntimeError("ImportError not raised")
        """
    )


# Verify that __path__ is respected for imports from the filesystem:
#
# * pyi_testmod_path/
#
#   * __init__.py -- inserts a/ into __path__, then imports b, which now refers to a/b.py, not ./b.py.
#   * b.py - raises an exception. **Should not be imported.**
#   * a/ -- contains no __init__.py.
#
#     * b.py - Empty. Should be imported.
@xfail(reason='__path__ not respected for filesystem modules.')
def test_import_respects_path(pyi_builder, script_dir):
    pyi_builder.test_source(
        'import pyi_testmod_path',
        pyi_args=['--additional-hooks-dir', str(script_dir / 'pyi_hooks')],
    )


# Verify correct handling of sys.meta_path redirects like pkg_resources 28.6.1 does: '_vendor.xxx' gets imported as
# 'extern.xxx' and using '__import__()'. Note: This also requires a hook, since 'pyi_testmod_metapath1._vendor' is not
# imported directly and won't be found by modulegraph.
def test_import_metapath1(pyi_builder, script_dir):
    pyi_builder.test_source(
        'import pyi_testmod_metapath1',
        pyi_args=['--additional-hooks-dir', str(script_dir / 'pyi_hooks')],
    )


@importorskip('PyQt5')
def test_import_pyqt5_uic_port(script_dir, pyi_builder):
    extra_path = _MODULES_DIR / 'pyi_import_pyqt_uic_port'
    pyi_builder.test_script(
        'pyi_import_pyqt5_uic_port.py',
        # Add the path to a fake PyQt5 package, used for this test.
        pyi_args=['--path', str(extra_path)]
    )


# Check whether modulegraph finds pyi_splash
def test_import_pyi_splash(pyi_builder):
    pyi_builder.test_source(
        """
        import pyi_splash
        assert hasattr(pyi_splash, "_initialized")
        """
    )


#--- unzipped .egg support ----


def test_egg_unzipped(pyi_builder):
    pathex = _MODULES_DIR / 'pyi_test_egg' / 'pyi_egg_unzipped.egg'
    hooks_dir = _MODULES_DIR / 'pyi_test_egg' / 'hooks'
    pyi_builder.test_source(
        """
        # This code is part of the package for testing eggs in `PyInstaller`.
        import os
        import pkg_resources

        # Test ability to load resource.
        expected_data = 'This is data file for `unzipped`.'.encode('ascii')
        t = pkg_resources.resource_string('unzipped_egg', 'data/datafile.txt')
        print('Resource: %s' % t)
        t_filename = pkg_resources.resource_filename('unzipped_egg', 'data/datafile.txt')
        print('Resource filename: %s' % t_filename)
        assert t.rstrip() == expected_data

        # Test ability that module from .egg is able to load resource.
        import unzipped_egg
        assert unzipped_egg.data == expected_data

        print('Okay.')
        """,
        pyi_args=['--paths', str(pathex), '--additional-hooks-dir', str(hooks_dir)],
    )  # yapf: disable


def test_egg_unzipped_metadata_pkg_resources(pyi_builder):
    pathex = _MODULES_DIR / 'pyi_test_egg' / 'pyi_egg_unzipped.egg'
    hooks_dir = _MODULES_DIR / 'pyi_test_egg' / 'hooks'
    pyi_builder.test_source(
        """
        import pkg_resources

        # Metadata should be automatically collected due to pkg_resources.get_distribution() call with literal argument
        # (which is picked up by PyInstaller's bytecode analysis).
        dist = pkg_resources.get_distribution('pyi_egg_unzipped')
        print(f"dist: {dist!r}")

        # Version is taken from metadata
        assert dist.version == '0.1', f"Unexpected version {dist.version!r}"
        # Project name is taken from egg name
        assert dist.project_name == 'pyi-egg-unzipped', f"Unexpected project name {dist.project_name!r}"
        """,
        pyi_args=['--paths', str(pathex), '--additional-hooks-dir', str(hooks_dir)],
    )  # yapf: disable


def test_egg_unzipped_metadata_importlib_metadata(pyi_builder):
    pathex = _MODULES_DIR / 'pyi_test_egg' / 'pyi_egg_unzipped.egg'
    hooks_dir = _MODULES_DIR / 'pyi_test_egg' / 'hooks'
    pyi_builder.test_source(
        """
        try:
            import importlib_metadata
        except ModuleNotFoundError:
            import importlib.metadata as importlib_metadata

        # Metadata should be automatically collected due to importlib_metadata.version() call with literal argument
        # (which is picked up by PyInstaller's bytecode analysis).
        version = importlib_metadata.version('pyi_egg_unzipped')
        print(f"version: {version!r}")
        assert version == '0.1', f"Unexpected version {version!r}"

        # NOTE: in contrast to pkg_resources, importlib_metadata seems to read the name from metadata instead of
        # deriving it from egg directory name.
        metadata = importlib_metadata.metadata('pyi_egg_unzipped')
        print(f"metadata: {metadata!r}")
        assert metadata['Name'] == 'unzipped-egg', f"Unexpected Name {metadata['Name']!r}"
        assert metadata['Version'] == '0.1', f"Unexpected Version {metadata['Version']!r}"

        dist = importlib_metadata.distribution('pyi_egg_unzipped')
        print(f"dist: {dist!r}")
        assert dist.name == 'unzipped-egg', f"Unexpected name {dist.name!r}"
        assert dist.version == '0.1', f"Unexpected version {dist.version!r}"
        """,
        pyi_args=['--paths', str(pathex), '--additional-hooks-dir', str(hooks_dir)],
    )  # yapf: disable


#--- namespaces ---


def test_nspkg1(pyi_builder):
    # Test inclusion of namespace packages implemented using pkg_resources.declare_namespace
    extra_paths = (_MODULES_DIR / 'nspkg1-pkg').glob('*.egg')
    paths_arg = os.pathsep.join([str(path) for path in extra_paths])
    pyi_builder.test_source(
        """
        import nspkg1.aaa
        import nspkg1.bbb.zzz
        import nspkg1.ccc
        """,
        pyi_args=['--paths', paths_arg],
    )


def test_nspkg1_empty(pyi_builder):
    # Test inclusion of a namespace-only packages in an zipped egg. This package only defines the namespace, nothing is
    # contained there.
    extra_paths = (_MODULES_DIR / 'nspkg1-pkg').glob('*.egg')
    paths_arg = os.pathsep.join([str(path) for path in extra_paths])
    pyi_builder.test_source(
        """
        import nspkg1
        print (nspkg1)
        """,
        pyi_args=['--paths', paths_arg],
    )


def test_nspkg1_bbb_zzz(pyi_builder):
    # Test inclusion of a namespace packages in an zipped egg
    extra_paths = (_MODULES_DIR / 'nspkg1-pkg').glob('*.egg')
    paths_arg = os.pathsep.join([str(path) for path in extra_paths])
    pyi_builder.test_source(
        """
        import nspkg1.bbb.zzz
        """,
        pyi_args=['--paths', paths_arg],
    )


def test_nspkg2(pyi_builder):
    # Test inclusion of namespace packages implemented as nspkg.pth-files
    extra_paths = [_MODULES_DIR / 'nspkg2-pkg']
    paths_arg = os.pathsep.join([str(path) for path in extra_paths])
    pyi_builder.test_source(
        """
        import nspkg2.aaa
        import nspkg2.bbb.zzz
        import nspkg2.ccc
        """,
        pyi_args=['--paths', paths_arg],
    )


@xfail(reason="modulegraph implements `pkgutil.extend_path` wrong")
def test_nspkg3(pyi_builder):
    extra_paths = (_MODULES_DIR / 'nspkg3-pkg').glob('*.egg')
    paths_arg = os.pathsep.join([str(path) for path in extra_paths])
    pyi_builder.test_source(
        """
        import nspkg3.aaa
        try:
            # pkgutil ignores items of sys.path that are not strings referring to existing directories. So this zipped
            # egg *must* be ignored.
            import nspkg3.bbb.zzz
        except ImportError:
            pass
        else:
            raise SystemExit('nspkg3.bbb.zzz found but should not')
        try:
            import nspkg3.a
        except ImportError:
            pass
        else:
            raise SystemExit('nspkg3.a found but should not')
        import nspkg3.ccc
        """,
        pyi_args=['--paths', paths_arg],
    )


def test_nspkg3_empty(pyi_builder):
    # Test inclusion of a namespace-only package in a zipped egg using pkgutil.extend_path. This package only defines
    # namespace, nothing is contained there.
    extra_paths = (_MODULES_DIR / 'nspkg3-pkg').glob('*_empty.egg')
    paths_arg = os.pathsep.join([str(path) for path in extra_paths])
    pyi_builder.test_source(
        """
        import nspkg3
        print (nspkg3)
        """,
        pyi_args=['--paths', paths_arg],
    )


def test_nspkg3_aaa(pyi_builder):
    # Test inclusion of a namespace package in an directory using pkgutil.extend_path
    extra_paths = (_MODULES_DIR / 'nspkg3-pkg').glob('*.egg')
    paths_arg = os.pathsep.join([str(path) for path in extra_paths])
    pyi_builder.test_source(
        """
        import nspkg3.aaa
        """,
        pyi_args=['--paths', paths_arg],
    )


def test_nspkg3_bbb_zzz(pyi_builder):
    # Test inclusion of a namespace package in an zipped egg using pkgutil.extend_path
    extra_paths = (_MODULES_DIR / 'nspkg3-pkg').glob('*.egg')
    paths_arg = os.pathsep.join([str(path) for path in extra_paths])
    pyi_builder.test_source(
        """
        import nspkg3.bbb.zzz
        """,
        pyi_args=['--paths', paths_arg],
    )


def test_nspkg_pep420(pyi_builder):
    # Test inclusion of PEP 420 namespace packages.
    extra_paths = (_MODULES_DIR / 'nspkg-pep420').glob('path*')
    paths_arg = os.pathsep.join([str(path) for path in extra_paths])
    pyi_builder.test_source(
        """
        import package.sub1
        import package.sub2
        import package.subpackage.sub
        import package.nspkg.mod
        """,
        pyi_args=['--paths', paths_arg],
    )


def test_nspkg_attributes(pyi_builder):
    # Test that non-PEP-420 namespace packages (e.g., the ones using
    # pkg_resources.declare_namespace) have proper attributes:
    #  * __path__ attribute should contain at least one path
    #  * __file__ attribute should point to an __init__ file within __path__
    extra_paths = (_MODULES_DIR / 'nspkg1-pkg').glob('*.egg')
    paths_arg = os.pathsep.join([str(path) for path in extra_paths])
    pyi_builder.test_source(
        """
        import os
        import nspkg1

        def validate_nspkg(pkg):
            from sys import version_info
            # Validate __path__
            path = getattr(pkg, '__path__', None)
            assert path is not None and len(path) >= 1, "invalid __path__"
            # Validate __file__
            file = pkg.__file__
            assert os.path.dirname(file) in path, \
                "dirname(__file__) does not point to __path__"
            assert os.path.basename(file).startswith('__init__.'), \
                "basename(__file__) does not start with __init__.!"

        validate_nspkg(nspkg1)
        """,
        pyi_args=['--paths', paths_arg],
    )


def test_nspkg_attributes_pep420(pyi_builder):
    # Test that PEP-420 namespace packages have proper attributes:
    #  * __path__ should contain at least one path
    #  * __file__ should be None
    extra_paths = (_MODULES_DIR / 'nspkg-pep420').glob('path*')
    paths_arg = os.pathsep.join([str(path) for path in extra_paths])
    pyi_builder.test_source(
        """
        import package
        import package.nspkg

        def validate_nspkg_pep420(pkg):
            from sys import version_info
            # Validate __path__
            path = getattr(pkg, '__path__', None)
            assert path is not None and len(path) >= 1, "invalid __path__"
            # Validate __file__
            assert getattr(pkg, '__file__') is None, "invalid __file__"

        validate_nspkg_pep420(package)
        validate_nspkg_pep420(package.nspkg)
        """,
        pyi_args=['--paths', paths_arg],
    )


#--- hooks related stuff ---


# imp leaks file handles.
@pytest.mark.filterwarnings("ignore", category=ResourceWarning)
def test_pkg_without_hook_for_pkg(pyi_builder, script_dir):
    # The package `pkg_without_hook_for_pkg` does not have a hook, but `pkg_without_hook_for_pkg.sub1` has one. And this
    # hook includes the "hidden" import `pkg_without_hook_for_pkg.sub1.sub11`
    pyi_builder.test_source(
        'import pkg_without_hook_for_pkg.sub1',
        pyi_args=['--additional-hooks-dir', str(script_dir / 'pyi_hooks')],
    )


def test_app_with_plugin(pyi_builder, data_dir):
    add_data_arg = f"{data_dir / 'static_plugin.py'}:."
    pyi_builder.test_script(
        'pyi_app_with_plugin.py',
        pyi_args=['--add-data', add_data_arg],
    )


def test_app_has_moved_error(pyi_builder, tmp_path):
    """
    Test graceful exit from the user moving/deleting the application whilst it's still running.
    """
    pyi_builder.test_source(
        f"""
        import os
        import sys
        os.rename(sys.executable, {repr(str(tmp_path / "something-else"))})
        try:
            # Import some non-builtin module which hasn't already been loaded.
            import csv
        except SystemExit:
            pass
        else:
            assert 0, "A system exit should have been raised."
        """
    )


def test_package_with_mixed_collection_mode(pyi_builder):
    # Test that PyInstaller's frozen importer and python's own `_frozen_importlib_external.PathFinder` complement, and
    # not exclude, each other. This is pre-requisite for having pure-python modules collected in PYZ archive, while
    # binary extensions (and some pure-python modules as well, if necessary) are collected as separate.
    pathex = _MODULES_DIR / 'pyi_mixed_collection_mode' / 'modules'
    hooks_dir = _MODULES_DIR / 'pyi_mixed_collection_mode' / 'hooks'
    pyi_builder.test_source(
        """
        import mypackage
        print(mypackage.a)
        print(mypackage.b)
        """,
        pyi_args=['--paths', str(pathex), '--additional-hooks-dir', str(hooks_dir)],
    )  # yapf: disable


# Tests for run-time sys.path modifications, typically with aim of exposing some part of a package to the outside world
# as a top-level package; for example, to expose a vendored package to the outside world. These tests aim to verify that
# we can handle dynamic sys.path modifications within PYZ-collected packages and honor the order of entries in sys.path.


# Shared implementation
def _test_sys_path_with_vendored_package(pyi_builder, modification_type, expected_string, extra_pyi_args=None):
    pathex = _MODULES_DIR / 'pyi_sys_path_with_vendored_package'

    pyi_args = [
        '--paths', str(pathex),
        '--hiddenimport', 'myotherpackage._vendored.mypackage.mod',
    ]  # yapf: disable

    if extra_pyi_args:
        pyi_args += extra_pyi_args

    # On macOS, also build and test .app bundle executable
    if is_darwin:
        pyi_args += ['--windowed']

    pyi_builder.test_source(
        f"""
        import myotherpackage
        myotherpackage.setup_vendored_packages('{modification_type}')

        import mypackage
        secret = mypackage.get_secret_string()
        assert secret == '{expected_string}', f"Unexpected secret string: {{secret!r}}"
        """,
        pyi_args=pyi_args,
    )


# In this scenario, we have only vendored package available - we intentionally suppress collection of stand-alone
# package during the build.
def test_sys_path_with_vendored_package_no_standalone(pyi_builder):
    _test_sys_path_with_vendored_package(pyi_builder, "append", "vendored", ["--exclude", "mypackage"])


# In this scenario, we have both stand-alone and vendored package available in sys.path; vendored package directory is
# appended to sys.path, so we expect to import the stand-alone version.
def test_sys_path_with_vendored_package_append(pyi_builder):
    _test_sys_path_with_vendored_package(pyi_builder, "append", "standalone")


# In this scenario, we have both stand-alone and vendored package available in sys.path; vendored package directory is
# prepended to sys.path, so we expect to import the vendored version.
def test_sys_path_with_vendored_package_prepend(pyi_builder):
    _test_sys_path_with_vendored_package(pyi_builder, "prepend", "vendored")


# Tests for run-time sys.path modifications that result in a PEP420 namespace package being split across different
# locations, both within the PYZ archive and in location external to frozen application.


# The test supports two import orders: standalone part, vendored part, external part; and reverse. Both orders are
# tested in case it matters whether the namespace package is first discovered by PyInstaller's frozen importer or by
# python's `_frozen_importlib_external.PathFinder`.
# Additionally, two sys.path modification strategies are tested: adding each new entry just before we import the
# corresponding module, or adding all entries in advance. Adding entries one by one should trigger recomputation
# of the `_NamespacePath` object on each subsequent import.
@pytest.mark.parametrize('import_order', ['forward', 'reverse'])
@pytest.mark.parametrize('path_modification', ['one_by_one', 'all_in_advance'])
def test_split_location_pep420_namespace_package(pyi_builder, import_order, path_modification):
    modules_root = _MODULES_DIR / 'pyi_split_location_pep420_namespace_package'

    pyi_args = [
        '--paths', str(modules_root / 'modules'),
        '--additional-hooks-dir', str(modules_root / 'hooks'),
        '--hiddenimport', 'myotherpackage._vendored.mynamespacepackage.vendored_pyz',
        '--hiddenimport', 'myotherpackage._vendored.mynamespacepackage.vendored_py',
    ]  # yapf: disable

    # On macOS, also build and test .app bundle executable
    if is_darwin:
        pyi_args += ['--windowed']

    # Path to external part needs to be passed to program via command-line arguments
    app_args = [os.path.join(modules_root, 'external-location')]

    # Test programs for all four combinations
    _test_programs = {}
    _test_programs[('forward', 'one_by_one')] = \
        """
        import sys

        external_path = sys.argv[1]
        from myotherpackage import vendored_path

        import mynamespacepackage.standalone_pyz
        print(mynamespacepackage.standalone_pyz)

        import mynamespacepackage.standalone_py
        print(mynamespacepackage.standalone_py)

        sys.path.append(vendored_path)
        import mynamespacepackage.vendored_pyz
        print(mynamespacepackage.vendored_pyz)

        import mynamespacepackage.vendored_py
        print(mynamespacepackage.vendored_py)

        sys.path.append(external_path)
        import mynamespacepackage.external_py
        print(mynamespacepackage.external_py)
        """
    _test_programs[('forward', 'all_in_advance')] = \
        """
        import sys

        external_path = sys.argv[1]
        from myotherpackage import vendored_path

        sys.path.append(vendored_path)
        sys.path.append(external_path)

        import mynamespacepackage.standalone_pyz
        print(mynamespacepackage.standalone_pyz)

        import mynamespacepackage.standalone_py
        print(mynamespacepackage.standalone_py)

        import mynamespacepackage.vendored_pyz
        print(mynamespacepackage.vendored_pyz)

        import mynamespacepackage.vendored_py
        print(mynamespacepackage.vendored_py)

        import mynamespacepackage.external_py
        print(mynamespacepackage.external_py)
        """
    _test_programs[('reverse', 'one_by_one')] = \
        """
        import sys

        external_path = sys.argv[1]
        from myotherpackage import vendored_path

        sys.path.insert(0, external_path)
        import mynamespacepackage.external_py
        print(mynamespacepackage.external_py)

        sys.path.insert(1, vendored_path)
        import mynamespacepackage.vendored_py
        print(mynamespacepackage.vendored_py)

        import mynamespacepackage.vendored_pyz
        print(mynamespacepackage.vendored_pyz)

        import mynamespacepackage.standalone_py
        print(mynamespacepackage.standalone_py)

        import mynamespacepackage.standalone_pyz
        print(mynamespacepackage.standalone_pyz)
        """
    _test_programs[('reverse', 'all_in_advance')] = \
        """
        import sys

        external_path = sys.argv[1]
        from myotherpackage import vendored_path

        sys.path.insert(0, external_path)
        sys.path.insert(1, vendored_path)

        import mynamespacepackage.external_py
        print(mynamespacepackage.external_py)

        import mynamespacepackage.vendored_py
        print(mynamespacepackage.vendored_py)

        import mynamespacepackage.vendored_pyz
        print(mynamespacepackage.vendored_pyz)

        import mynamespacepackage.standalone_py
        print(mynamespacepackage.standalone_py)

        import mynamespacepackage.standalone_pyz
        print(mynamespacepackage.standalone_pyz)
        """

    # Build and run the appropriate test program
    pyi_builder.test_source(
        _test_programs[(import_order, path_modification)],
        pyi_args=pyi_args,
        app_args=app_args,
    )
