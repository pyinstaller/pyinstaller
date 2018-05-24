#-----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Interactive tests are successful when they are able to run
the executable for some time. Otherwise it is marked as fail.

Note: All tests in this file should use the argument 'runtime'.
"""
import pytest

from PyInstaller.utils.tests import importorskip, xfail
from PyInstaller.compat import is_win

_RUNTIME = 10  # In seconds.


@importorskip('IPython')
@pytest.mark.skipif(is_win, reason='See issue #3535.')
def test_ipython(pyi_builder):
    pyi_builder.test_source(
        """
        from IPython import embed
        embed()
        """, runtime=_RUNTIME)


@xfail(reason='TODO - known to fail')
@importorskip('PySide')
def test_pyside(pyi_builder):
    pyi_builder.test_script('pyi_interact_pyside.py', #pyi_args=['--windowed'],
                            runtime=_RUNTIME)
