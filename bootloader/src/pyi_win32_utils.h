/*
 * ****************************************************************************
 * Copyright (c) 2013-2023, PyInstaller Development Team.
 *
 * Distributed under the terms of the GNU General Public License (version 2
 * or later) with exception for distributing the bootloader.
 *
 * The full license is in the file COPYING.txt, distributed with this software.
 *
 * SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
 * ****************************************************************************
 */

/*
 * Windows-specific helper functions.
 */

#ifndef PYI_WIN32_UTILS_H
#define PYI_WIN32_UTILS_H

#ifdef _WIN32

#include <windows.h>

typedef struct _pyi_context PYI_CONTEXT;

char *GetWinErrorString(DWORD error_code);

char *pyi_win32_utils_to_utf8(char *buffer, const wchar_t *str, size_t n);
wchar_t *pyi_win32_utils_from_utf8(wchar_t *buffer, const char *ostr, size_t n);

char *pyi_win32_utf8_to_mbs(char * dst, const char * src, size_t max);

int pyi_win32_initialize_security_descriptor(PYI_CONTEXT *pyi_ctx);
void pyi_win32_free_security_descriptor(PYI_CONTEXT *pyi_ctx);

int pyi_win32_mkdir(const wchar_t *path, const PSECURITY_DESCRIPTOR security_descriptor);

int pyi_win32_is_symlink(const wchar_t *path);

int pyi_win32_realpath(const wchar_t *path, wchar_t *resolved_path);

int pyi_win32_is_drive_root(const wchar_t *path);

#if !defined(WINDOWED)

void pyi_win32_hide_console();
void pyi_win32_minimize_console();

#endif /* !defined(WINDOWED) */

#endif /* _WIN32 */

#endif  /* PYI_WIN32_UTILS_H */
