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
