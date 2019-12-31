#-----------------------------------------------------------------------------
# Copyright (c) 2005-2020, PyInstaller Development Team.
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

from PyInstaller.utils.tests import importorskip, xfail, skipif_notwin
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


@skipif_notwin
@xfail(reason='May fail on CI - Should succeed on local run')
@pytest.mark.parametrize("bit_count", [24, 32])
def test_windows_pyi_splash(pyi_builder_spec, capfd, monkeypatch, bit_count):
    """
    Test to check if the bootloader is able to display a splash
    screen with either 24bit or 32bit image on Windows.
    """
    monkeypatch.setenv('_TEST_SPLASH_BITCOUNT', str(bit_count))
    pyi_builder_spec.test_spec('spec_with_splash.spec',
                               runtime=_RUNTIME)

    # Check if commands worked
    out, err = capfd.readouterr()
    assert 'SPLASH: Launching Splash screen' in err
    assert 'SPLASH: Closing splash screen' in err
