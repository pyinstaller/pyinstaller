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

#ifdef _WIN32

#include <windows.h>
#include <commctrl.h> /* InitCommonControls */
#include <stdio.h>    /* _fileno */
#include <io.h>       /* _get_osfhandle */
#include <signal.h>   /* signal */

/* PyInstaller headers. */
#include "pyi_global.h"  /* PATH_MAX */
#include "pyi_main.h"
#include "pyi_utils.h"
#include "pyi_win32_utils.h"

#ifndef IO_REPARSE_TAG_SYMLINK
    #define IO_REPARSE_TAG_SYMLINK 0xA000000CL
#endif

#define ERROR_STRING_MAX 4096
static char errorString[ERROR_STRING_MAX];

/* GetWinErrorString
 *
 * Return a pointer to a null-terminated string containing a textual description of the
 * given error code. If the error code is zero, the result of GetLastError() is used.
 * The text is localized and ANSI-encoded. The caller is not responsible for freeing
 * this pointer.
 *
 * Returns a pointer to statically-allocated storage. Not thread safe.
 */

char * GetWinErrorString(DWORD error_code) {
    wchar_t local_buffer[ERROR_STRING_MAX];
    DWORD result;

    if (error_code == 0) {
        error_code = GetLastError();
    }
    /* Note: Giving 0 to dwLanguageID means MAKELANGID(LANG_NEUTRAL,
     * SUBLANG_NEUTRAL), but we should use SUBLANG_DEFAULT instead of
     * SUBLANG_NEUTRAL. Please see the note written in
     * "Language Identifier Constants and Strings" on MSDN.
     * https://docs.microsoft.com/en-us/windows/desktop/intl/language-identifier-constants-and-strings
     */
    result = FormatMessageW(
        FORMAT_MESSAGE_FROM_SYSTEM, // dwFlags
        NULL,                       // lpSource
        error_code,                 // dwMessageID
        MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT), // dwLanguageID
        local_buffer,               // lpBuffer
        ERROR_STRING_MAX,           // nSize
        NULL                        // Arguments
        );

    if (!result) {
        FATAL_WINERROR("FormatMessageW", "No error messages generated.\n");
        return "PyInstaller: FormatMessageW failed.";
    }
    if (!pyi_win32_utils_to_utf8(errorString,
                                 local_buffer,
                                 ERROR_STRING_MAX)) {
        return "PyInstaller: pyi_win32_utils_to_utf8 failed.";
    }
    return errorString;
}

/* Convert a wide string to an ANSI string.
 *
 *  Returns a newly allocated buffer containing the ANSI characters terminated by a null
 *  character. The caller is responsible for freeing this buffer with free().
 *
 *  Returns NULL and logs error reason if encoding fails.
 */

char *
pyi_win32_wcs_to_mbs(const wchar_t *wstr)
{
    DWORD len, ret;
    char * str;

    /* NOTE: CP_ACP means "current ANSI codepage" which is set in the
     * "Language for Non-Unicode Programs" control panel setting. */

    /* Get buffer size by passing NULL and 0 for output arguments */
    len = WideCharToMultiByte(CP_ACP,  /* CodePage */
                              0,       /* dwFlags */
                              wstr,    /* lpWideCharStr */
                              -1,      /* cchWideChar - length in chars */
                              NULL,    /* lpMultiByteStr */
                              0,       /* cbMultiByte - length in bytes */
                              NULL,    /* lpDefaultChar */
                              NULL     /* lpUsedDefaultChar */
                              );

    if (0 == len) {
        FATAL_WINERROR("WideCharToMultiByte", "Failed to get ANSI buffer size.\n");
        return NULL;
    }

    str = (char *)calloc(len + 1, sizeof(char));
    if (str == NULL) {
        FATAL_WINERROR("win32_wcs_to_mbs", "Out of memory.\n");
        return NULL;
    };

    ret = WideCharToMultiByte(CP_ACP,    /* CodePage */
                              0,         /* dwFlags */
                              wstr,      /* lpWideCharStr */
                              -1,        /* cchWideChar - length in chars */
                              str,       /* lpMultiByteStr */
                              len,       /* cbMultiByte - length in bytes */
                              NULL,      /* lpDefaultChar */
                              NULL       /* lpUsedDefaultChar */
                              );

    if (0 == ret) {
        FATAL_WINERROR("WideCharToMultiByte", "Failed to encode filename as ANSI.\n");
        return NULL;
    }
    return str;
}

/*
 * Encode wchar_t (UTF16) into char (UTF8).
 *
 * `wstr` must be null-terminated.
 *
 * If `str` is not NULL, copies the result into the given buffer, which must hold
 * at least `len` bytes. Returns the given buffer if successful. Returns NULL on
 * encoding failure, or if the UTF-8 encoding requires more than `len` bytes.
 *
 * If `str` is NULL, allocates and returns a new buffer to store the result. The
 * `len` argument is ignored. Returns NULL on encoding failure. The caller is
 * responsible for freeing the returned buffer using free().
 *
 */
char *
pyi_win32_utils_to_utf8(char *str, const wchar_t *wstr, size_t len)
{
    char * output;

    if (NULL == str) {
        /* Get buffer size by passing NULL and 0 for output arguments
         * -1 for cchWideChar means string is null-terminated
         */
        len = WideCharToMultiByte(CP_UTF8,              /* CodePage */
                                  0,                    /* dwFlags */
                                  wstr,                 /* lpWideCharStr */
                                  -1,                   /* cchWideChar - length in chars */
                                  NULL,                 /* lpMultiByteStr */
                                  0,                    /* cbMultiByte - length in bytes */
                                  NULL,                 /* lpDefaultChar */
                                  NULL                  /* lpUsedDefaultChar */
                                  );

        if (0 == len) {
            FATAL_WINERROR("WideCharToMultiByte", "Failed to get UTF-8 buffer size.\n");
            return NULL;
        }

        output = (char *)calloc(len + 1, sizeof(char));
        if (output == NULL) {
            FATAL_WINERROR("win32_utils_to_utf8", "Out of memory.\n");
            return NULL;
        };
    }
    else {
        output = str;
    }

    len = WideCharToMultiByte(CP_UTF8,              /* CodePage */
                              0,                    /* dwFlags */
                              wstr,                 /* lpWideCharStr */
                              -1,                   /* cchWideChar - length in chars */
                              output,               /* lpMultiByteStr */
                              (DWORD)len,           /* cbMultiByte - length in bytes */
                              NULL,                 /* lpDefaultChar */
                              NULL                  /* lpUsedDefaultChar */
                              );

    if (len == 0) {
        FATAL_WINERROR("WideCharToMultiByte",
                       "Failed to encode wchar_t as UTF-8.\n");
        return NULL;
    }
    return output;
}

/*
 * Decode char (UTF8) into wchar_t (UTF16).
 *
 * `str` must be null-terminated.
 *
 * If `wstr` is not NULL, copies the result into the given buffer, which must hold
 * at least `wlen` characters. Returns the given buffer if successful. Returns NULL on
 * encoding failure, or if the UTF-16 encoding requires more than `wlen` characters.
 *
 * If `wstr` is NULL, allocates and returns a new buffer to store the result. The
 * `wlen` argument is ignored. Returns NULL on encoding failure. The caller is
 * responsible for freeing the returned buffer using free().
 */

wchar_t *
pyi_win32_utils_from_utf8(wchar_t *wstr, const char *str, size_t wlen)
{
    wchar_t * output;

    if (NULL == wstr) {
        /* Get buffer size by passing NULL and 0 for output arguments
         * -1 for cbMultiByte means string is null-terminated.
         */
        wlen = MultiByteToWideChar(CP_UTF8,             /* CodePage */
                                   0,                   /* dwFlags */
                                   str,                 /* lpMultiByteStr */
                                   -1,                  /* cbMultiByte - length in bytes */
                                   NULL,                /* lpWideCharStr */
                                   0                    /* cchWideChar - length in chars */
                                   );

        if (0 == wlen) {
            FATAL_WINERROR("MultiByteToWideChar", "Failed to get wchar_t buffer size.\n");
            return NULL;
        }

        output = (wchar_t *)calloc(wlen + 1, sizeof(wchar_t));
        if (output == NULL) {
            FATAL_WINERROR("win32_utils_from_utf8", "Out of memory.\n");
            return NULL;
        };
    }
    else {
        output = wstr;
    }

    wlen = MultiByteToWideChar(CP_UTF8,              /* CodePage */
                               0,                    /* dwFlags */
                               str,                  /* lpMultiByteStr */
                               -1,                   /* cbMultiByte - length in bytes */
                               output,               /* lpWideCharStr */
                               (DWORD)wlen           /* cchWideChar - length in chars */
                               );

    if (wlen == 0) {
        FATAL_WINERROR("MultiByteToWideChar", "Failed to decode wchar_t from UTF-8\n");
        return NULL;
    }
    return output;
}

/* Convert an UTF-8 string to an ANSI string.
 *
 *  Returns NULL if encoding fails.
 */
char *
pyi_win32_utf8_to_mbs(char * dst, const char * src, size_t max)
{
    wchar_t * wsrc;
    char * mbs;

    wsrc = pyi_win32_utils_from_utf8(NULL, src, 0);

    if (NULL == wsrc) {
        return NULL;
    }

    mbs = pyi_win32_wcs_to_mbs(wsrc);

    free(wsrc);

    if (NULL == mbs) {
        return NULL;
    }

    if (dst) {
        strncpy(dst, mbs, max);
        free(mbs);
        return dst;
    }
    else {
        return mbs;
    }
}

/* Check if the given path is a symbolic link. */
int pyi_win32_is_symlink(const wchar_t *path)
{
    WIN32_FIND_DATAW info;
    HANDLE ret;

    ret = FindFirstFileExW(path, FindExInfoBasic, &info, FindExSearchNameMatch, NULL, 0);
    if (ret == INVALID_HANDLE_VALUE) {
        /* Failed to look up path; assume it is not symbolic link */
        return 0;
    }
    FindClose(ret);

    if (info.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT) {
        if (info.dwReserved0 == IO_REPARSE_TAG_SYMLINK) {
            return 1;
        }
    }

    return 0;
}

/* Equivalent of `realpath()` function on POSIX systems; canonicalize
 * the given path and resolve symbolic links */
int pyi_win32_realpath(const wchar_t *path, wchar_t *resolved_path)
{
    HANDLE handle;
    DWORD ret;

    /* Open file/directory handle */
    handle = CreateFileW(
        path, /* lpFileName */
        0, /* dwDesiredAccess */
        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, /* dwShareMode */
        NULL, /* lpSecurityAttributes */
        OPEN_EXISTING, /* dwCreationDisposition */
        FILE_ATTRIBUTE_NORMAL, /* dwFlagsAndAttributes*/
        NULL /* hTemplateFile */
    );
    if (handle == INVALID_HANDLE_VALUE) {
        return -1;
    }

    /* Fully resolve the path */
    ret = GetFinalPathNameByHandleW(
        handle,  /* hFile */
        resolved_path, /* lpszFilePath */
        PATH_MAX, /* cchFilePath */
        FILE_NAME_NORMALIZED /* dwFlags */
    );

    CloseHandle(handle);

    if (ret == 0 || ret >= PATH_MAX) {
        /* Failure or insufficient buffer size */
        return  -1;
    }

    return 0;
}


/* Check if the given path is just a drive letter */
int pyi_win32_is_drive_root(const wchar_t *path)
{
    /* For now, handle just drive letter, optionally followed by the path separator.
       E.g., "C:" or "Z:\".
     */
    size_t len;

    len = wcslen(path);
    if (len == 2 || len == 3) {
        /* First character must be a letter */
        if (!iswalpha(path[0])) {
            return 0;
        }
        /* Second character must be the colon */
        if (path[1] != L':') {
            return 0;
        }
        /* Third character, if present, must be the Windows directory separator */
        if (len > 2 && (path[2] != L'\\')) {
            return 0;
        }

        return 1;
    }

    return 0;
}


#endif /* _WIN32 */
