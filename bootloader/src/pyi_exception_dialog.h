/*
 * ****************************************************************************
 * Copyright (c) 2021-2023, PyInstaller Development Team.
 *
 * Distributed under the terms of the GNU General Public License (version 2
 * or later) with exception for distributing the bootloader.
 *
 * The full license is in the file COPYING.txt, distributed with this software.
 *
 * SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
 * ****************************************************************************
 */

#ifndef PYI_EXCEPTION_DIALOG_H
#define PYI_EXCEPTION_DIALOG_H

#if defined(WINDOWED) && defined(_WIN32)

int pyi_unhandled_exception_dialog(const char *script_name, const char *exception_message, const char *traceback);

#endif /* defined(WINDOWED) && defined(_WIN32) */

#endif /* PYI_EXCEPTION_DIALOG_H */
