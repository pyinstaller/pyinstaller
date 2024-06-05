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
Tests for splash screen.

NOTE: splash screen is not supported on macOS due to incompatible design.
"""

import pytest

from PyInstaller.compat import is_darwin, is_musl


# Test that splash screen is successfully started. This is an "interactive"
# test (see test_interactive.py), where we expect the program to run for
# specified amount of time, before we terminate it.
@pytest.mark.skipif(is_darwin, reason="Splash screen is not supported on macOS.")
@pytest.mark.parametrize("build_mode", ['onedir', 'onefile'])
@pytest.mark.parametrize("with_tkinter", [False, True], ids=['notkinter', 'tkinter'])
@pytest.mark.xfail(is_musl, reason="musl + tkinter is known to cause mysterious segfaults.")
def test_splash_screen_running(pyi_builder_spec, capfd, monkeypatch, build_mode, with_tkinter):
    if build_mode == 'onefile':
        monkeypatch.setenv('_TEST_SPLASH_BUILD_MODE', 'onefile')
    if with_tkinter:
        monkeypatch.setenv('_TEST_SPLASH_WITH_TKINTER', '1')

    pyi_builder_spec.test_spec(
        'spec_with_splash.spec',
        runtime=10,  # Interactive test - terminate test program after 10 seconds.
    )

    out, err = capfd.readouterr()
    assert 'SPLASH: splash screen started' in err, \
        f"Cannot find log entry indicating start of splash screen in:\n{err}"
