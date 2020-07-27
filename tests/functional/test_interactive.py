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
from PyInstaller.compat import is_win, is_darwin

_RUNTIME = 10  # In seconds.


@importorskip('IPython')
@pytest.mark.skipif(is_win, reason='See issue #3535.')
def test_ipython(pyi_builder):
    pyi_builder.test_source(
        """
        from IPython import embed
        embed()
        """, runtime=_RUNTIME)


# Someone with a Mac needs to take a look into implementing this the right way
# If Splash discovers standalone binaries on a Mac those will be bundled and
# the test should succeed, if the system provided Tcl/Tk is used PyInstaller
# does not find the standalone binaries
@xfail(is_darwin, reason="MacOS uses system-wide Tcl/Tk, which"
                         " is not necessarily bundled.")
@pytest.mark.parametrize("mode", ['onedir', 'onefile'])
def test_pyi_splash(pyi_builder_spec, capfd, monkeypatch, mode):
    if mode == 'onefile':
        monkeypatch.setenv('_TEST_SPLASH_ONEFILE', 'onefile')

    pyi_builder_spec.test_spec('spec_with_splash.spec',
                               runtime=_RUNTIME)

    out, err = capfd.readouterr()
    assert 'SPLASH: Splash screen started' in err, \
        ("Cannot find log entry indicating start of splash screen in:\n{}"
         .format(err))
