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
@pytest.mark.parametrize("build_mode", ['onedir', 'onefile'])
@pytest.mark.parametrize("with_tkinter", [False, True], ids=['notkinter', 'tkinter'])
@pytest.mark.xfail(is_musl, reason="musl + tkinter is known to cause mysterious segfaults.")
def test_pyi_splash(pyi_builder_spec, capfd, monkeypatch, build_mode, with_tkinter):
    if build_mode == 'onefile':
        monkeypatch.setenv('_TEST_SPLASH_BUILD_MODE', 'onefile')
    if with_tkinter:
        monkeypatch.setenv('_TEST_SPLASH_WITH_TKINTER', '1')

    pyi_builder_spec.test_spec('spec_with_splash.spec', runtime=_RUNTIME)

    out, err = capfd.readouterr()
    assert 'SPLASH: Splash screen started' in err, \
        f"Cannot find log entry indicating start of splash screen in:\n{err}"
