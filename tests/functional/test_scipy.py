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
Functional tests for SciPy.
"""

import sys

import pytest

from PyInstaller.utils.tests import importorskip, xfail, onedir_only

pytestmark = [
    importorskip('scipy'),
    xfail(
        sys.version_info[:3] == (3, 12, 0),
        reason='SciPy is broken with PyInstaller and python 3.12.0 (#7992).',
    ),
]


# Basic import test for each scipy module, to ensure that each module is importable on its own. Due to amount of tests,
# run them only in onedir mode.
@pytest.mark.parametrize(
    'module', [
        'scipy',
        'scipy.cluster',
        'scipy.constants',
        'scipy.datasets',
        'scipy.fft',
        'scipy.fftpack',
        'scipy.integrate',
        'scipy.interpolate',
        'scipy.io',
        'scipy.linalg',
        'scipy.misc',
        'scipy.ndimage',
        'scipy.odr',
        'scipy.optimize',
        'scipy.signal',
        'scipy.sparse',
        'scipy.spatial',
        'scipy.special',
        'scipy.stats',
    ]
)
@onedir_only
def test_scipy(pyi_builder, module):
    pyi_builder.test_source(f"""
        import {module}
        """)
