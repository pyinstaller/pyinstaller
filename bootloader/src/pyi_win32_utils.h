/*
 * ****************************************************************************
 * Copyright (c) 2013-2016, PyInstaller Development Team.
 * Distributed under the terms of the GNU General Public License with exception
 * for distributing bootloader.
 *
 * The full license is in the file COPYING.txt, distributed with this software.
 * ****************************************************************************
 */

/* TODO Convert this file to file ./common/pyi_win32_utils.h */
#ifndef UTILS_H
#define UTILS_H

#ifdef _WIN32

char * GetWinErrorString();
int CreateActContext(const char *manifestpath);

char * pyi_win32_wcs_to_mbs(const wchar_t *wstr);
char * pyi_win32_wcs_to_mbs_sfn(const wchar_t *wstr);

char ** pyi_win32_argv_to_utf8(int argc, wchar_t **wargv);
wchar_t ** pyi_win32_wargv_from_utf8(int argc, char **argv);

char * pyi_win32_utils_to_utf8(char *buffer, const wchar_t *str, size_t n);
wchar_t * pyi_win32_utils_from_utf8(wchar_t *buffer, const char *ostr, size_t n);

char * pyi_win32_utf8_to_mbs_ex(char * dst, const char * src, size_t max, int sfn);
char * pyi_win32_utf8_to_mbs(char * dst, const char * src, size_t max);
char * pyi_win32_utf8_to_mbs_sfn(char * dst, const char * src, size_t max);

char * pyi_win32_utf8_to_mbs_sfn_keep_basename(char * dest, const char * src);

char ** pyi_win32_argv_mbcs_from_utf8_ex(int argc, char **wargv, int sfn);
char ** pyi_win32_argv_mbcs_from_utf8(int argc, char **wargv);
char ** pyi_win32_argv_mbcs_from_utf8_sfn(int argc, char **wargv);

#endif /* ifdef _WIN32 */

#endif  /* UTILS_H */
