#-----------------------------------------------------------------------------
# Copyright (c) 2005-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
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
