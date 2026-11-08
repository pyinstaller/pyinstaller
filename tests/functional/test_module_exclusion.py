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

import pathlib

import pytest

from PyInstaller.utils.tests import importorskip, requires

# Run the tests here in onedir mode only - onefile offers no additional insights in this context.
pytestmark = pytest.mark.parametrize('pyi_builder', ['onedir'], indirect=True)

# Directory with testing modules used in some tests.
_MODULES_DIR = pathlib.Path(__file__).parent / 'modules'


# Test module exclusion; ensure that excluded modules are not collected. When exclusion is performed via hooks, also
# test that hooks for excluded modules are not ran (by having hooks raise exceptions).
@pytest.mark.parametrize(
    "exclude_args,exclude_hooks", (
        pytest.param(True, False, id='args'),
        pytest.param(False, True, id='hooks'),
        pytest.param(True, True, id='args-and-hooks'),
    )
)
def test_module_exclusion(exclude_args, exclude_hooks, pyi_builder):
    pyi_args = ['--paths', str(_MODULES_DIR / 'pyi_module_exclusion' / 'modules')]
    if exclude_args:
        pyi_args += ['--exclude', 'mymodule_feature2', '--exclude', 'mymodule_feature3']
    if exclude_hooks:
        pyi_args += ['--additional-hooks-dir', str(_MODULES_DIR / 'pyi_module_exclusion' / 'hooks')]

    pyi_builder.test_source(
        """
        import mymodule_main

        # Feature #1 module should be included, and thus available
        assert mymodule_main.feature1_available == True

        # Feature #2 module should be excluded, and thus unavailable
        assert mymodule_main.feature2_available == False

        # Feature #3 module should be excluded, and thus unavailable
        assert mymodule_main.feature3_available == False
        """,
        pyi_args=pyi_args,
        run_from_path=True
    )


# Tests for excluded subpackage from the top-level package hook. Ensure that such subpackage is excluded when the only
# reference comes from within the corresponding top-level package (or one of its submodules/subpackages). However, if
# the subpackage is referred from external source (e.g., user's program), then it should be collected and the exclusion
# rule from the top-level package hook should not block collection of submodules from that subpackage.
@pytest.mark.parametrize("with_reference", [False, True], ids=["noref", "ref"])
def test_subpackage_exclusion(pyi_builder, with_reference):
    pyi_args = [
        '--paths',
        str(_MODULES_DIR / 'pyi_excluded_subpackage' / 'modules'),
        '--additional-hooks-dir',
        str(_MODULES_DIR / 'pyi_excluded_subpackage' / 'hooks'),
    ]

    if with_reference:
        # Explicit reference to excluded subpackage in user's program; we expect the subpackage to be fully collected.
        source_code = (
            """
            import mypackage.optional  # is importable if its submodules are also collected.
            assert mypackage.optional.optional_function() == 42
            """
        )
    else:
        # No reference to excluded subpackage other than in top-level package; we expect the subpackage to be excluded.
        source_code = (
            """
            import importlib.util

            import mypackage

            # Ensure the optional subpackage is unavailable
            optional_spec = importlib.util.find_spec('mypackage.optional')
            assert optional_spec == None, "mypackage.optional is collected, but should not be!"
            """
        )

    pyi_builder.test_source(
        source_code,
        pyi_args=pyi_args,
    )


# Our hook for sqlalchemy excludes sqlalchemy.testing. Make sure explicitly importing the said subpackage works.
# See #9193.
@importorskip('sqlalchemy')
def test_subpackage_exclusion_sqlalchemy_testing(pyi_builder):
    pyi_builder.test_source("""
        import sqlalchemy.testing
        """)


# Our hook for numpy excludes numpy.f2py for numpy < 2.0. Make sure explicitly importing the said subpackage works.
@requires('numpy < 2.0')
def test_subpackage_exclusion_numpy_f2py(pyi_builder):
    pyi_builder.test_source("""
        import numpy.f2py
        """)


# Test that a relative import attempt of a missing optional sub-module in a package does not trigger collection of an
# unrelated but eponymous top-level module. Simulates the scenario from #8010, where the following block in
# `openpyxl.reader.excel`:
#
# ```
# try:
#    from ..tests import KEEP_VBA
# except ImportError:
#    KEEP_VBA = False
# ```
#
# (https://foss.heptapod.net/openpyxl/openpyxl/-/blob/branch/3.1/openpyxl/reader/excel.py#L16)
#
# triggers collection of top-level `tests` package that is provided by the `LaoNLP` distribution. And importing
# the said `tests` package during analysis triggers LaoNLP's unit tests...
def test_missing_relative_import_collects_unrelated_top_level_module(pyi_builder):
    extra_path = _MODULES_DIR / "pyi_missing_relative_import"
    hooks_dir = extra_path / 'hooks'

    pyi_builder.test_source(
        """
        import mypackage
        """,
        pyi_args=['--additional-hooks-dir', str(hooks_dir), '--paths', str(extra_path)]
    )  # yapf: disable


# Test that various forms of relative imports are properly caught by the module exclusion.
@pytest.mark.parametrize('exclude', [False, True], ids=["baseline", "exclude"])
def test_excluded_relative_imports(pyi_builder, exclude):
    extra_path = _MODULES_DIR / "pyi_excluded_relative_imports"
    hooks_dir = extra_path / 'hooks'

    pyi_args = ['--paths', str(extra_path)]
    if exclude:
        pyi_args += ['--additional-hooks-dir', str(hooks_dir)]

    pyi_builder.test_source(
        f"""
        import os
        os.environ['_FORBIDDEN_MODULES_ENABLED'] = '{str(int(not exclude))}'  # '0' or '1'

        import mypackage
        """,
        pyi_args=pyi_args,
    )
