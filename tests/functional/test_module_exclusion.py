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
