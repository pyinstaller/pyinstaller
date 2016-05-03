#-----------------------------------------------------------------------------
# Copyright (c) 2005-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

"""
Functional tests for SciPy.
"""

from PyInstaller.compat import is_darwin, is_win
from PyInstaller.utils.tests import importorskip, skip, xfail


@xfail(is_win, reason='Issue scipy/scipy#5461.')
@xfail(is_darwin, reason='Issue #1895.')
@importorskip('scipy')
def test_scipy(pyi_builder):
    pyi_builder.test_source(
        """
        from distutils.version import LooseVersion

        # Test top-level SciPy importability.
        import scipy
        from scipy import *

        # Test hooked SciPy modules.
        import scipy.io.matlab
        import scipy.sparse.csgraph

        # Test problematic SciPy modules.
        import scipy.linalg
        import scipy.signal

        # SciPy >= 0.16 privatized the previously public "scipy.lib" package as
        # "scipy._lib". Since this package is problematic, test its
        # importability regardless of SciPy version.
        if LooseVersion(scipy.__version__) >= LooseVersion('0.16.0'):
            import scipy._lib
        else:
            import scipy.lib
        """)


@skip(reason='Issue #1919.')
@xfail(is_win, reason='Issue scipy/scipy#5461.')
@xfail(is_darwin, reason='Issue #1895.')
@importorskip('scipy')
def test_scipy_special(pyi_builder):
    """
    Test the importability of the `scipy.special` package and related hooks.

    This importation _must_ be tested independent of the importation of all
    other problematic SciPy packages and modules. Combining this test with other
    SciPy tests (e.g., `test_scipy()`) fails to properly exercise the hidden
    imports required by this package.
    """
    pyi_builder.test_source("""import scipy.special""")
