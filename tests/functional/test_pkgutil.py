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

import os
import pathlib

import pytest

from PyInstaller.compat import exec_python_rc
from PyInstaller.utils.tests import importable, xfail, onedir_only, onefile_only

# Directory with testing modules used in some tests.
_MODULES_DIR = pathlib.Path(__file__).parent / 'modules'


# Tests for pkgutil.get_data().
def test_pkgutil_get_data(pyi_builder):
    add_data_arg = f"{_MODULES_DIR / 'pkg3' / 'sample-data.txt'}:pkg3"
    pyi_builder.test_source(
        """
            import pkgutil
            import pkg3  # Serves as a hiddenimport

            expected_data = b'This is data text for testing the packaging module data.'

            data = pkgutil.get_data('pkg3', 'sample-data.txt')
            print("Read data: {data!r}")
            if not data:
                raise SystemExit('Error: Could not read data with pkgutil.get_data().')

            if data.strip() != expected_data:
                raise SystemExit('Error: Read data does not match expected data!')
        """,
        pyi_args=['--add-data', add_data_arg],
    )


@xfail(reason='Our import mechanism returns the wrong loader-class for __main__.')
def test_pkgutil_get_data__main__(pyi_builder):
    add_data_arg = f"{_MODULES_DIR / 'pkg3' / 'sample-data.txt'}:pkg3"
    pyi_builder.test_source(
        """
        import pkgutil

        expected_data = b'This is data text for testing the packaging module data.'

        data = pkgutil.get_data('__main__', 'pkg3/sample-data.txt')
        if not data:
            raise SystemExit('Error: Could not read data with pkgutil.get_data().')

        if data.strip() != expected_data:
            raise SystemExit('Error: Read data does not match expected data!')
        """,
        pyi_args=['--add-data', add_data_arg],
    )


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
def test_pkgutil_iter_modules(package, script_dir, tmp_path, pyi_builder, archive, resolve_pkg_path=False):
    # Ensure package is available
    if not importable(package.split(".")[0]):
        pytest.skip(f"Needs {package}")

    # Full path to test script
    test_script = script_dir / 'pyi_pkgutil_iter_modules.py'

    # Run unfrozen test script
    out_unfrozen = tmp_path / 'output-unfrozen.txt'
    rc = exec_python_rc(str(test_script), package, '--output-file', str(out_unfrozen))
    assert rc == 0
    # Read results
    results_unfrozen = _read_results_file(out_unfrozen)

    # Run frozen script
    out_frozen = tmp_path / 'output-frozen.txt'
    debug_args = ['--debug', 'noarchive'] if archive == 'noarchive' else []
    pyi_builder.test_script(
        test_script,
        pyi_args=[
            # ensure everything is collected
            '--collect-submodules', package,
            # enable/disable noarchive
            *debug_args,
        ],
        app_args=[package, '--output-file', str(out_frozen)] + (['--resolve-pkg-path'] if resolve_pkg_path else [])
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
@onefile_only
def test_pkgutil_iter_modules_resolve_pkg_path(script_dir, tmp_path, pyi_builder):
    # A single combination (altgraph package, archive mode) is enough to check for proper symlink handling.
    test_pkgutil_iter_modules('json', script_dir, tmp_path, pyi_builder, archive=True, resolve_pkg_path=True)


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
@onedir_only
def test_pkgutil_iter_modules_macos_app_bundle(script_dir, tmp_path, pyi_builder, monkeypatch):
    pathex = _MODULES_DIR / 'pyi_pkgutil_itermodules' / 'package'
    hooks_dir = _MODULES_DIR / 'pyi_pkgutil_itermodules' / 'hooks'
    package = 'mypackage'

    # Full path to test script
    test_script = script_dir / 'pyi_pkgutil_iter_modules.py'

    # Run unfrozen test script
    env = os.environ.copy()
    if 'PYTHONPATH' in env:
        pathex = os.pathsep.join([str(pathex), env['PYTHONPATH']])
    env['PYTHONPATH'] = str(pathex)
    out_unfrozen = tmp_path / 'output-unfrozen.txt'
    rc = exec_python_rc(str(test_script), package, '--output-file', str(out_unfrozen), env=env)
    assert rc == 0
    # Read results
    results_unfrozen = _read_results_file(out_unfrozen)

    # Freeze the test program
    # This also runs both executables (POSIX build and .app bundle) with same arguments, so we have no way of separating
    # the output file. Therefore, we will manually re-run the executables ourselves.
    pyi_builder.test_script(
        test_script,
        pyi_args=[
            '--paths', str(pathex),
            '--hiddenimport', package,
            '--additional-hooks-dir', str(hooks_dir),
            '--windowed',  # enable .app bundle
        ],
        app_args=[package],
    )  # yapf: disable

    # Run each executable and verify its output
    executables = pyi_builder._find_executables('pyi_pkgutil_iter_modules')
    assert executables
    for idx, exe in enumerate(executables):
        out_frozen = tmp_path / f"output-frozen-{idx}.txt"
        rc = pyi_builder._run_executable(
            exe,
            args=[package, '--output-file', str(out_frozen)],
            run_from_path=False,
            runtime=None,
        )
        assert rc == 0
        results_frozen = _read_results_file(out_frozen)
        print("RESULTS", results_frozen, "\n\n")

        assert results_unfrozen == results_frozen


# Explicitly test that in macOS .app bundles, modules can be iterated regardless of whether the given search path is
# anchored in the Contents/Frameworks directory (the "true" sys._MEIPASS) or the Contents/Resources directory.
# A real-world example would involve a package that is partially collected into PYZ, but its `__init__` module is
# collected as source .py file only. Thus, the search path derived from fully resolved __file__ attribute would end up
# pointing to Resources directory instead of Frameworks one. For the purpose of the test, however, we simply modify the
# search path ourselves.
#
# This is more explicit version of test_pkgutil_iter_modules_macos_app_bundle, just in case.
@pytest.mark.darwin
@onedir_only
def test_pkgutil_iter_modules_macos_app_bundle_alternative_search_path(pyi_builder):
    pyi_builder.test_source(
        """
        import os
        import sys
        import pkgutil
        import json  # Our test package

        # Check that we are running in .app bundle mode. If not, exit.
        print("sys._MEIPASS:", sys._MEIPASS)
        if not sys._MEIPASS.endswith("Contents/Frameworks"):
            print("Not running as .app bundle.")
            sys.exit(0)

        alternative_top_level_dir = os.path.join(os.path.dirname(sys._MEIPASS), 'Resources')

        def _compare_path_contents(true_path, alternative_path, prefix=""):
            # Iterate over modules using path anchored to "true" top-level directory (sys._MEIPASS).
            print(f"Iterating over modules in path anchored to true top-level directory - {true_path!r}:")
            modules1 = list(pkgutil.iter_modules([true_path], prefix))
            for entry in modules1:
                print(entry)
            print("")

            assert len(modules1) > 0, "Modules list is emtpy?!"

            # Iterate over modules using path anchored to "alternative" top-level directory.
            print(f"Iterating over modules in path anchored to alternative top-level directory {alternative_path!r}:")
            modules2 = list(pkgutil.iter_modules([alternative_path], prefix))
            for entry in modules2:
                print(entry)
            print("")

            # We can compare only .name and .ispkg, because .module_finder might be per-path instance.
            def _to_comparable_list(modules):
                return sorted([(module.name, module.ispkg) for module in modules])

            assert _to_comparable_list(modules1) == _to_comparable_list(modules2), "Lists of modules do not match!"
            print("OK!")

        # First, run comparison on top-level application directory
        print("Running test for top-level application directory...")
        _compare_path_contents(
            sys._MEIPASS,
            alternative_top_level_dir,
        )

        # Repeat for the 'json' package
        print("Running test for 'json' package...")
        _compare_path_contents(
            os.path.join(sys._MEIPASS, 'json'),
            os.path.join(alternative_top_level_dir, 'json'),
            prefix='json.',
        )
        """,
        pyi_args=['--collect-submodules', 'json', '--windowed']
    )


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
