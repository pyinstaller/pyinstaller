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
 * Global shared functions used in many bootloader files. This file
 * contains implementations that are specific to Windows.
 */

#ifdef _WIN32

#include <stdio.h>
#include <stdarg.h>  /* va_list, va_start(), va_end() */

#include <windows.h>
#include <direct.h>
#include <process.h>
#include <io.h>

/* PyInstaller headers. */
#include "pyi_global.h"
#include "pyi_utils.h"


/**********************************************************************\
 *               Debug and error message implementation               *
\**********************************************************************/
/* On Windows, we print messages to stderr if console is available. If
 * not, we use message box for error/warning messages, and
 * OutputDebugStringW function for debug messages. */

/* Maximum length of text displayed in a message box. */
#define MBTXTLEN 1024


/* Return a pointer to a null-terminated string containing a textual
 * description of the given error code. Used by pyi_debug_dialog_winerror
 * and pyi_debug_winerror.
 *
 * NOTE: this function currently returns UTF-8 encoded string, converted
 * from wide-char string. It would be better to return wide-char string,
 * but the callers are currently formatting their strings in UTF-8. Once
 * that is changed, this implementation can be simplified.
 */
static const char *
_pyi_get_winerror_string(DWORD error_code)
{
    #define ERROR_STRING_MAX 4096
    static wchar_t local_buffer_w[ERROR_STRING_MAX];
    static char local_buffer[ERROR_STRING_MAX];

    DWORD result;

    /* Note: Giving 0 to dwLanguageID means MAKELANGID(LANG_NEUTRAL,
     * SUBLANG_NEUTRAL), but we should use SUBLANG_DEFAULT instead of
     * SUBLANG_NEUTRAL. Please see the note written in "Language
     * Identifier Constants and Strings" on MSDN.
     * https://docs.microsoft.com/en-us/windows/desktop/intl/language-identifier-constants-and-strings
     */
    result = FormatMessageW(
        FORMAT_MESSAGE_FROM_SYSTEM, /* dwFlags */
        NULL, /* lpSource */
        error_code, /* dwMessageId */
        MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT), /* dwLanguageId */
        local_buffer_w, /* lpBuffer */
        ERROR_STRING_MAX, /* nSize */
        NULL /* Arguments */
    );

    if (!result) {
        return "PyInstaller: FormatMessageW failed.";
    }

    if (pyi_win32_wcs_to_utf8(local_buffer_w, local_buffer, ERROR_STRING_MAX) == NULL) {
        return "PyInstaller: pyi_win32_wcs_to_utf8 failed.";
    }

    return local_buffer;
}


#if defined(WINDOWED)

/*
 * Dialogs used in Windows windowed/noconsole builds.
 */

static void
_pyi_show_message_box(const char *msg, const wchar_t *caption, UINT uType)
{
    wchar_t msg_w[MBTXTLEN];

    /* The original message is formatted in UTF-8; convert it to
     * wide-char for MessageBoxW. */
    if (pyi_win32_utf8_to_wcs(msg, msg_w, MBTXTLEN)) {
        MessageBoxW(NULL, msg_w, caption, MB_OK | uType);
    } else {
        /* Conversion failed. Try displaying the original UTF-8 string
         * via the ANSI method. This will produce garbled text if Unicode
         * characters are present, but it is better than nothing. */
        MessageBoxA(NULL, msg, "Error/warning (ANSI fallback)", MB_OK | uType);
    }
}

void
pyi_debug_dialog_error(const char *fmt, ...)
{
    char msg[MBTXTLEN];
    va_list args;

    va_start(args, fmt);
    vsnprintf(msg, MBTXTLEN, fmt, args);
    va_end(args);

    _pyi_show_message_box(msg, L"Error", MB_ICONEXCLAMATION);
}

void
pyi_debug_dialog_warning(const char *fmt, ...)
{
    char msg[MBTXTLEN];
    va_list args;

    va_start(args, fmt);
    vsnprintf(msg, MBTXTLEN, fmt, args);
    va_end(args);

    _pyi_show_message_box(msg, L"Warning", MB_ICONWARNING);
}

void
pyi_debug_dialog_winerror(const char *funcname, const char *fmt, ...)
{
    char fullmsg[MBTXTLEN];
    char msg[MBTXTLEN];
    DWORD error_code = GetLastError();
    va_list args;

    va_start(args, fmt);
    vsnprintf(msg, MBTXTLEN, fmt, args);
    va_end(args);

    /* Suppress warnings generated by some mingw64 gcc toolchains;
     * we do not care about truncation here. */
    #pragma GCC diagnostic push
    #pragma GCC diagnostic ignored "-Wformat-truncation"
    snprintf(fullmsg, MBTXTLEN, "%s%s: %s", msg, funcname, _pyi_get_winerror_string(error_code));
    #pragma GCC diagnostic pop

    _pyi_show_message_box(fullmsg, L"Error", MB_ICONEXCLAMATION);
}

void
pyi_debug_dialog_perror(const char *funcname, const char *fmt, ...)
{
    char fullmsg[MBTXTLEN];
    char msg[MBTXTLEN];
    va_list args;

    va_start(args, fmt);
    vsnprintf(msg, MBTXTLEN, fmt, args);
    va_end(args);

    /* Suppress warnings generated by some mingw64 gcc toolchains;
     * we do not care about truncation here. */
    #pragma GCC diagnostic push
    #pragma GCC diagnostic ignored "-Wformat-truncation"
    snprintf(fullmsg, MBTXTLEN, "%s%s: %s", msg, funcname, strerror(errno));
    #pragma GCC diagnostic pop

    _pyi_show_message_box(fullmsg, L"Error", MB_ICONEXCLAMATION);
}

/* Emit debug messages (in debug-enabled builds) via OutputDebugString
 * win32 API. */
#ifdef LAUNCH_DEBUG

void
pyi_debug_win32debug(const char *fmt, ...)
{
    char msg[MBTXTLEN];
    wchar_t msg_w[MBTXTLEN];
    va_list args;
    int pid_len;

    /* Add pid to the message */
    pid_len = sprintf(msg, "[%d] ", getpid());

    /* Format message */
    va_start(args, fmt);
    vsnprintf(&msg[pid_len], MBTXTLEN-pid_len, fmt, args);
    va_end(args);

    /* Convert message from UTF-8 to wide-char for OutputDebugStringW */
    if (pyi_win32_utf8_to_wcs(msg, msg_w, MBTXTLEN)) {
        OutputDebugStringW(msg_w);
    } else {
        /* Conversion failed; try displaying the original UTF-8 string
         * via the ANSI method. This will produce garbled text if Unicode
         * characters are present, but it is better than nothing. */
        OutputDebugStringA(msg);
    }
}

void
pyi_debug_win32debug_w(const wchar_t *fmt, ...)
{
    wchar_t msg[MBTXTLEN];
    va_list args;
    int pid_len;

    /* Add pid to the message */
    pid_len = _swprintf(msg, L"[%d] ", getpid());

    /* Format message */
    va_start(args, fmt);
    _vsnwprintf(&msg[pid_len], MBTXTLEN-pid_len, fmt, args);
    va_end(args);

    /* Submit to OutputDebugStringW */
    OutputDebugStringW(msg);
}

#endif /* ifdef LAUNCH_DEBUG */

#else /* defined(WINDOWED) */


/*
 * Print messages to stderr.
 */

/* Format string in UTF-8, then convert to wide-char and display using
 * fwprintf(). Used by pyi_debug_printf, pyi_debug_perror, and
 * pyi_debug_winerror helpers. */
static void
_pyi_vprintf_to_stderr(const char *fmt, va_list v)
{
    #define BUFSIZE (MBTXTLEN * 2)
    char msg[BUFSIZE];
    wchar_t msg_w[BUFSIZE];

    vsnprintf(msg, BUFSIZE, fmt, v);

    if (pyi_win32_utf8_to_wcs(msg, msg_w, BUFSIZE)) {
        fwprintf(stderr, L"%ls", msg_w);
    } else {
        /* Conversion failed; try displaying the original UTF-8 string
         * via the ANSI method. This will produce garbled text if Unicode
         * characters are present, but it is better than nothing. Also,
         * we should not be mixing ANSI and wide-char I/O, although
         * Windows seems to be quite forgiving in this regard (i.e.,
         * stream orientation does not seem to matter). */
        fprintf(stderr, "[ANSI fallback]: %s", msg);
    }
}

/* Print a message. Used by PYI_ERROR and PYI_WARNING macros, and by
 * PYI_DEBUG macro in debug-enabled builds. */
void
pyi_debug_printf(const char *fmt, ...)
{
    va_list v;

    /* Print the [PID] prefix. */
    fwprintf(stderr, L"[%d] ", getpid());

    /* Print the message */
    va_start(v, fmt);
    _pyi_vprintf_to_stderr(fmt, v);
    va_end(v);
}

/* Wide-char variant of pyi_debug_printf. Used by PYI_DEBUG_W macro. */
void
pyi_debug_printf_w(const wchar_t *fmt, ...)
{
    va_list v;

    /* Print the [PID] prefix */
    fwprintf(stderr, L"[%d] ", getpid());

    /* Print the message */
    va_start(v, fmt);
    vfwprintf(stderr, fmt, v);
    va_end(v);
}


/* Print a message, followed by the name of the function that resulted
 * in an error and a textual description of the error, obtained via
 * perror(). Used by PYI_PERROR macro. */
void
pyi_debug_perror(const char *funcname, const char *fmt, ...)
{
    va_list v;

    /* Formatted message */
    va_start(v, fmt);
    _pyi_vprintf_to_stderr(fmt, v);
    va_end(v);

    /* Perror-formatted error message */
    /* TODO: we should be using _wperror() here! However, Windows seems
     * to be quite forgiving about mixing ANSI and wide-char I/O (i.e.,
     * stream orientation does not seem to matter). */
    perror(funcname); /* perror() writes to stderr */
}

/* Print a message, followed by the name of the function that resulted
 * in an error and a textual description of the error, obtained via
 * FormatMessage win32 API. Used by PYI_WINERROR macro. */
static void
_pyi_printf_to_stderr(const char *fmt, ...)
{
    va_list v;

    va_start(v, fmt);
    _pyi_vprintf_to_stderr(fmt, v);
    va_end(v);
}

void
pyi_debug_winerror(const char *funcname, const char *fmt, ...)
{
    va_list v;
    DWORD error_code = GetLastError();

    va_start(v, fmt);
    _pyi_vprintf_to_stderr(fmt, v);
    va_end(v);

    _pyi_printf_to_stderr("%s: %s", funcname, _pyi_get_winerror_string(error_code));
}


#endif  /* defined(WINDOWED) */

#endif /* ifdef(_WIN32) */
