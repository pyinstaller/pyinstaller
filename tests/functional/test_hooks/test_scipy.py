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

from PyInstaller.compat import is_py312
from PyInstaller.utils.tests import importorskip, xfail


@importorskip('scipy')
@xfail(is_py312, reason='SciPy is broken with PyInstaller and python 3.12 (#7992).')
def test_scipy_toplevel(pyi_builder):
    pyi_builder.test_source("""
        import scipy
    """)


@importorskip('scipy')
@xfail(is_py312, reason='SciPy is broken with PyInstaller and python 3.12 (#7992).')
def test_scipy(pyi_builder):
    pyi_builder.test_source(
        """
        # Test top-level SciPy importability.
        import scipy

        # Test hooked SciPy modules.
        import scipy.io.matlab
        import scipy.sparse.csgraph

        # Test problematic SciPy modules.
        import scipy.linalg
        import scipy.signal

        # SciPy >= 0.16 privatized the previously public "scipy.lib" package as "scipy._lib".
        # Since this package is problematic, test its importability regardless of its private status.
        import scipy._lib
        """
    )


@importorskip('scipy')
@xfail(is_py312, reason='SciPy is broken with PyInstaller and python 3.12 (#7992).')
def test_scipy_special(pyi_builder):
    """
    Test the importability of the `scipy.special` package and related hooks.

    This importation _must_ be tested independent of the importation of all other problematic SciPy packages
    and modules. Combining this test with other SciPy tests (e.g., `test_scipy()`) fails to properly exercise
    the hidden imports required by this package.
    """
    pyi_builder.test_source("""import scipy.special""")
