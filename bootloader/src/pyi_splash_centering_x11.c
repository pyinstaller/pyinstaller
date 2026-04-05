/*
 * ****************************************************************************
 * Copyright (c) 2026, PyInstaller Development Team.
 *
 * Distributed under the terms of the GNU General Public License (version 2
 * or later) with exception for distributing the bootloader.
 *
 * The full license is in the file COPYING.txt, distributed with this software.
 *
 * SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
 * ****************************************************************************
 */

#include "pyi_splash.h"

#if !defined(_WIN32) && !defined(__APPLE__)

int _pyi_splash_setup_centering_mode_x11(int mode, int *x, int *y, int *width, int *height)
{
    PYI_DEBUG("SPLASH: TODO - implement splash-screen centering for X11/(X)Wayland!\n");
    return -1;
}

#endif
