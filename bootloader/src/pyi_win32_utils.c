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

/* TODO move this code to file  pyi_win32.c. */

/*
 * Functions in this file are windows specific and are mostly related to handle
 * Side-by-Side assembly:
 *
 * https://en.wikipedia.org/wiki/Side-by-side_assembly
 */

#ifdef _WIN32

#include <windows.h>
#include <commctrl.h> /* InitCommonControls */
#include <stdio.h>    /* _fileno */
#include <io.h>       /* _get_osfhandle */
#include <signal.h>   /* signal */
#include <sddl.h>     /* ConvertStringSecurityDescriptorToSecurityDescriptorW */

/* PyInstaller headers. */
#include "pyi_global.h"  /* PATH_MAX */
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

/* We shouldn't need to convert ANSI to wchar_t since everything is provided as wchar_t */

/* The following are used to convert the UTF-16 strings provided by Windows
 * into UTF-8 so we can store them in the `char *` variables and fields
 * we use on Linux. Storing them like this is a wart, but storing them as `wchar_t *`
 * and converting back and forth everywhere on Linux/OS X is an even bigger wart
 */

/* Convert elements of wargv to UTF-8 */

char **
pyi_win32_argv_to_utf8(int argc, wchar_t **wargv)
{
    int i, j;
    char ** argv;

    argv = (char **)calloc(argc + 1, sizeof(char *));
    if (argv == NULL) {
        return NULL;
    };

    for (i = 0; i < argc; i++) {
        argv[i] = pyi_win32_utils_to_utf8(NULL, wargv[i], 0);

        if (NULL == argv[i]) {
            goto err;
        }
    }
    argv[argc] = NULL;

    return argv;
err:

    for (j = 0; j <= i; j++) {
        free(argv[j]);
    }
    free(argv);
    return NULL;
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


/* Retrieve the SID for the specified token information class from the current process.
 *
 * At the moment, TokenUser and TokenAppContainerSid are supported.
 *
 * Used in a compatibility work-around for wine, which at the time of writing
 * (version 5.0.2) does not properly support SID S-1-3-4 (directory owner),
 * and therefore user's actual SID must be used instead.
 *
 * Returns a copy of SID string on success, NULL on failure (or if the SID is unavailable
 * or zero-length). The returned string must be freed using LocalFree().
 */
static wchar_t *
_pyi_win32_get_sid(TOKEN_INFORMATION_CLASS token_information_class)
{
    HANDLE process_token = INVALID_HANDLE_VALUE;
    DWORD token_info_size = 0;
    void *token_info = NULL;
    wchar_t *sid = NULL;

    /* Get access token for the calling process */
    if (!OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &process_token)) {
        goto cleanup;
    }

    /* Query buffer size and allocate buffer */
    if (!GetTokenInformation(process_token, token_information_class, NULL, 0, &token_info_size)) {
        if (GetLastError() != ERROR_INSUFFICIENT_BUFFER) {
            goto cleanup;
        }
    }
    if (token_info_size == 0) {
        /* As per MSDN, in the Microsoft implementation, if number or size is zero, calloc
         * returns a pointer to an allocated block of non-zero size. An attempt to read or
         * write through the returned pointer leads to undefined behavior. */
        goto cleanup;
    }
    token_info = calloc(1, token_info_size);
    if (!token_info) {
        goto cleanup;
    }

    /* Get token information */
    if (!GetTokenInformation(process_token, token_information_class, token_info, token_info_size, &token_info_size)) {
        goto cleanup;
    }

    /* Convert SID to string */
    switch (token_information_class)
    {
        case TokenUser: {
            PTOKEN_USER user_info = (PTOKEN_USER)token_info;
            ConvertSidToStringSidW(user_info->User.Sid, &sid);
            break;
        }
        case TokenAppContainerSid: {
            PTOKEN_APPCONTAINER_INFORMATION app_container_info = (PTOKEN_APPCONTAINER_INFORMATION)token_info;
            ConvertSidToStringSidW(app_container_info->TokenAppContainer, &sid);
            break;
        }
        default: {
            /* Unsupoorted token information class */
            break;
        }
    }

    // Cleanup
cleanup:
    free(token_info);
    if (process_token != INVALID_HANDLE_VALUE) {
        CloseHandle(process_token);
    }

    return sid;
}

/* Security descriptor applied to application's temporary directory and its
 * sub-directories, which are created by `pyi_win32_mkdir`. Must be explicitly
 * initialized via `pyi_win32_initialize_security_descriptor`, and freed via
 * `pyi_win32_free_security_descriptor`.
 */
static PSECURITY_DESCRIPTOR security_descriptor = NULL;

/* Initialize security descriptor applied to application's temporary directory and its
 * sub-directories.
 */
int
pyi_win32_initialize_security_descriptor()
{
    wchar_t *user_sid = NULL;
    wchar_t *app_container_sid = NULL;
    wchar_t security_descriptor_str[PATH_MAX];
    int ret;

    user_sid = _pyi_win32_get_sid(TokenUser); /* Resolve user's SID for compatibility with wine */

    /* If program is running within an AppContainer, the app container SID has to be added to
     * the DACL, otherwise our process will not have access to the temporary directory. */
    app_container_sid = _pyi_win32_get_sid(TokenAppContainerSid); /* NULL when not running in AppContainer */

    /* DACL descriptor D:dacl_flags(string_ace1)(string_ace2)
     * with ACE string:
     * ace_type;ace_flags;rights;object_guid;inherit_object_guid;account_sid;(resource_attribute)
     * - ace_type = SDDL_ACCESS_ALLOWED (A)
     * - rights = SDDL_FILE_ALL (FA)
     * - account_sid = current user (queried SID)
     */
    if (app_container_sid) {
        ret = _snwprintf(
            security_descriptor_str,
            PATH_MAX,
            L"D:(A;;FA;;;%s)(A;;FA;;;%s)",
            user_sid ? user_sid : L"S-1-3-4",
            app_container_sid);
    } else {
        ret = _snwprintf(
            security_descriptor_str,
            PATH_MAX,
            L"D:(A;;FA;;;%s)",
            user_sid ? user_sid : L"S-1-3-4");
    }

    LocalFree(user_sid); /* Must be freed using LocalFree() */
    LocalFree(app_container_sid); /* Must be freed using LocalFree() */

    if (ret >= PATH_MAX) {
        OTHERERROR("Security descriptor string length exceeds PATH_MAX!\n");
        return -1;
    }

    /* Convert security descriptor string to security descriptor */
    VS("LOADER: initializing security descriptor from string: %S\n", security_descriptor_str);
    ret = ConvertStringSecurityDescriptorToSecurityDescriptorW(
        security_descriptor_str,
        SDDL_REVISION_1,
        &security_descriptor,
        NULL);
    if (ret == 0) {
        return -1;
    }

    return 0;
}

/* Free security descriptor applied to application's temporary directory and its
 * sub-directories.
 */
void
pyi_win32_free_security_descriptor()
{
    LocalFree(security_descriptor);
    security_descriptor = NULL;
}


/* Create a directory at path with restricted permissions.
 *
 * The directory owner will be the only one with permissions on the created
 * dir. Calling this function is equivalent to calling chmod(path, 0700) on
 * POSIX systems.
 *
 * Requires initialization of security descriptor by calling
 * `pyi_win32_initialize_security_descriptor` prior to first attempt at
 * creating directory with this function.
 *
 * Returns 0 on success, -1 on error.
 */
int
pyi_win32_mkdir(const wchar_t *path)
{
    /* Set up security attributes with pre-initialized security descriptor.
     * `pyi_win32_initialize_security_descriptor()` must have been called
     * prior to calling this function.
     */
    SECURITY_ATTRIBUTES security_attr;

    if (!security_descriptor) {
        OTHERERROR("Security descriptor is not initialized!\n");
        return -1;
    }

    security_attr.nLength = sizeof(SECURITY_ATTRIBUTES);
    security_attr.bInheritHandle = FALSE;
    security_attr.lpSecurityDescriptor = security_descriptor;

    /* Create directory */
    if (!CreateDirectoryW(path, &security_attr)) {
        return -1;
    };
    return 0;
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

#if !defined(WINDOWED)

/* Helper that hides or minimizes the console window
 * if it is owned by the process. The show_cmd argument
 * is passed to the ShowWindow call, and should be
 * either SW_HIDE or SW_SHOWMINNOACTIVE.
 */
static void pyi_win32_adjust_console(int show_cmd)
{
    HWND hConsole = GetConsoleWindow();
    if (hConsole != NULL) {
        DWORD dwProcessId = GetCurrentProcessId();
        DWORD dwConsoleProcessId;

        if (GetWindowThreadProcessId(hConsole, &dwConsoleProcessId) == 0) {
            return;  /* Window handle is invalid */
        }

        if (dwProcessId == dwConsoleProcessId) {
            ShowWindow(hConsole, show_cmd);
        }
    }
}

void pyi_win32_hide_console()
{
    pyi_win32_adjust_console(SW_HIDE);
}

void pyi_win32_minimize_console()
{
    pyi_win32_adjust_console(SW_SHOWMINNOACTIVE);
}

#endif


#endif  /* _WIN32 */
