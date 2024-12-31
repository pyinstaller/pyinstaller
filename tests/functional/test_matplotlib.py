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
"""
Functional tests for Matplotlib.
"""

import pytest

from PyInstaller.utils.tests import importorskip
from PyInstaller.utils.hooks import check_requirement

# List of tuples "(backend_name, qt_bindings)", where:
#
# * "backend_name" is the name of a Matplotlib backend to be tested below.
# * "qt_bindings" is the name of the external Qt bindings package required by this backend.
#
if check_requirement("matplotlib >= 3.5.0"):
    # Matplotlib 3.5.0 introduced a unified Qt backend that supports PySide2, PyQt5, PySide6, and PyQt6.
    _backends = [
        ('QtAgg', 'PyQt5'),
        ('QtAgg', 'PySide2'),
        ('QtAgg', 'PyQt6'),
        ('QtAgg', 'PySide6'),
    ]
else:
    _backends = [
        ('Qt5Agg', 'PyQt5'),
        ('Qt5Agg', 'PySide2'),
    ]


# Test Matplotlib with access to only one backend at a time.
@importorskip('matplotlib')
@pytest.mark.parametrize(
    'backend_name, qt_bindings',
    [
        pytest.param(backend_name, qt_bindings, marks=importorskip(qt_bindings))
        for backend_name, qt_bindings in _backends
    ],
    ids=[qt_bindings for backend_name, qt_bindings in _backends],
)
def test_matplotlib(pyi_builder, monkeypatch, backend_name, qt_bindings):
    '''
    Test Matplotlib with the passed backend enabled, the passed backend package included with this frozen application,
    all other backend packages explicitly excluded from this frozen application, and the passed rcParam key set to the
    corresponding passed value if that key is _not_ `None` or ignore that value otherwise.
    '''

    # Exclude all Qt bindings except the ones we are using in this test.
    pyi_args = [
        f'--exclude-module={bindings_name}' for backend_name, bindings_name in _backends if bindings_name != qt_bindings
    ]

    # Test program
    pyi_builder.test_source(
        f"""
        import os
        import sys
        import tempfile

        import matplotlib

        # Matplotlib >= v3.4.0 allows Qt bindings name in QT_API environment variable to be capitalized. Lower-case it
        # here just in case we ever happen to run the test with older version.
        qt_bindings_lower = {qt_bindings!r}.lower()

        # Report these parameters.
        print(f'Testing Matplotlib with backend={backend_name} and QT_API={{qt_bindings_lower}}')

        # Configure Matplotlib *BEFORE* calling any Matplotlib functions.
        matplotlib.rcParams['backend'] = {backend_name!r}
        os.environ['QT_API'] = qt_bindings_lower

        # Enable the desired backend *BEFORE* plotting with this backend.
        matplotlib.use({backend_name!r})

        # A runtime hook should force Matplotlib to create its configuration directory in a temporary directory
        # rather than in $HOME/.matplotlib.
        configdir = os.environ['MPLCONFIGDIR']
        print(f'MPLCONFIGDIR: {{configdir}}')
        if not configdir.startswith(tempfile.gettempdir()):
            raise SystemExit('MPLCONFIGDIR not pointing to temp directory.')

        # Test access to the standard 'mpl_toolkits' namespace package installed with Matplotlib.
        # Note that this import was reported to fail under Matplotlib 1.3.0.
        from mpl_toolkits import axes_grid1

        # Try importing pyplot. This will attempt to activate the selected backend.
        from matplotlib import pyplot as plt
        """,
        pyi_args=pyi_args,
    )
