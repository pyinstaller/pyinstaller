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
Interactive tests are successful when they are able to run the executable for some time.
Otherwise it is marked as fail.

Note: All tests in this file should use the argument 'runtime'.
"""
import pytest

from PyInstaller.utils.tests import importorskip
from PyInstaller.compat import is_win, is_darwin, is_musl

_RUNTIME = 10  # In seconds.


@importorskip('IPython')
@pytest.mark.skipif(is_win, reason='See issue #3535.')
def test_ipython(pyi_builder):
    pyi_builder.test_source("""
        from IPython import embed
        embed()
        """, runtime=_RUNTIME)


# Splash screen is not supported on macOS due to incompatible design.
@pytest.mark.skipif(is_darwin, reason="Splash screen is not supported on macOS.")
@pytest.mark.parametrize("mode", ['onedir', 'onefile'])
@pytest.mark.xfail(is_musl, reason="musl + tkinter is known to cause mysterious segfaults.")
def test_pyi_splash(pyi_builder_spec, capfd, monkeypatch, mode):
    if mode == 'onefile':
        monkeypatch.setenv('_TEST_SPLASH_ONEFILE', 'onefile')

    pyi_builder_spec.test_spec('spec_with_splash.spec', runtime=_RUNTIME)

    out, err = capfd.readouterr()
    assert 'SPLASH: Splash screen started' in err, \
        "Cannot find log entry indicating start of splash screen in:\n{}".format(err)
