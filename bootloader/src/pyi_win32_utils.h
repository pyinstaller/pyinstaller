/*
 * ****************************************************************************
 * Copyright (c) 2013-2021, PyInstaller Development Team.
 *
 * Distributed under the terms of the GNU General Public License (version 2
 * or later) with exception for distributing the bootloader.
 *
 * The full license is in the file COPYING.txt, distributed with this software.
 *
 * SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
 * ****************************************************************************
 */

/* TODO Convert this file to file ./common/pyi_win32_utils.h */
#ifndef UTILS_H
#define UTILS_H

#ifdef _WIN32

char * GetWinErrorString(DWORD error_code);

char ** pyi_win32_argv_to_utf8(int argc, wchar_t **wargv);
wchar_t ** pyi_win32_wargv_from_utf8(int argc, char **argv);

char * pyi_win32_utils_to_utf8(char *buffer, const wchar_t *str, size_t n);
wchar_t * pyi_win32_utils_from_utf8(wchar_t *buffer, const char *ostr, size_t n);

char * pyi_win32_utf8_to_mbs(char * dst, const char * src, size_t max);

int pyi_win32_mkdir(const wchar_t *path);

int pyi_win32_is_drive_root(const wchar_t *path);

#endif /* ifdef _WIN32 */

#endif  /* UTILS_H */
