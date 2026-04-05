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

#if defined(_WIN32)

int _pyi_splash_setup_centering_mode_win32(int mode, int *x, int *y, int *width, int *height)
{
    switch (mode) {
        case SPLASH_CENTER_VIRTUAL_SCREEN: {
            /* NOTE: this is not DPI aware, and will likely give wrong
             * results with mixed-DPI screens... */
            *x = 0;
            *y = 0;
            *width = GetSystemMetrics(SM_CXVIRTUALSCREEN);
            *height = GetSystemMetrics(SM_CYVIRTUALSCREEN);
            break;
        }
        case SPLASH_CENTER_PRIMARY_SCREEN:
        case SPLASH_CENTER_ACTIVE_SCREEN:  {
            POINT mouse_pos;
            HMONITOR monitor;
            MONITORINFO monitor_info;

            if (mode == SPLASH_CENTER_PRIMARY_SCREEN) {
                mouse_pos.x = 0;
                mouse_pos.y = 0;
                monitor = MonitorFromPoint(mouse_pos, MONITOR_DEFAULTTOPRIMARY);
            } else {
                if (!GetCursorPos(&mouse_pos)) {
                    PYI_DEBUG_W(L"SPLASH: failed to obtain cursor position!\n");
                    return -1;
                }
                monitor = MonitorFromPoint(mouse_pos, MONITOR_DEFAULTTONEAREST);
            }

            if (!monitor) {
                PYI_DEBUG_W(L"SPLASH: failed to obtain monitor handle!\n");
                return -1;
            }

            /* Query monitor info */
            memset(&monitor_info, 0, sizeof(MONITORINFO));
            monitor_info.cbSize = sizeof(MONITORINFO);
            if (!GetMonitorInfoW(monitor, &monitor_info)) {
                PYI_DEBUG_W(L"SPLASH: failed to query monitor info!\n");
                return -1;
            }

            *x = monitor_info.rcMonitor.left;
            *y = monitor_info.rcMonitor.top;
            *width = monitor_info.rcMonitor.right - monitor_info.rcMonitor.left;
            *height = monitor_info.rcMonitor.bottom - monitor_info.rcMonitor.top;

            break;
        }
        default: {
            return -1; /* Not handled */
        }
    }

    return 0;
}

#endif
