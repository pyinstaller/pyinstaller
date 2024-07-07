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

/* Having a header included outside of the ifdef block prevents the compilation
 * unit from becoming empty, which is disallowed by pedantic ISO C. */
#include "pyi_global.h"

#ifdef _WIN32

#include <stdio.h>
#include <stdarg.h>  /* va_list, va_start(), va_end() */

#include <windows.h>
#include <direct.h>
#include <process.h>
#include <io.h>

/* PyInstaller headers. */
#include "pyi_utils.h"


/**********************************************************************\
 *               Debug and error message implementation               *
\**********************************************************************/
/* On Windows, we print messages to stderr if console is available. If
 * not, we use message box for error/warning messages, and
 * OutputDebugString function for debug messages. */

/* Maximum length of debug/warning/error messages */
#define PYI_MESSAGE_LEN 4096


/* Common message formatting helpers used by both console and
 * noconsole/windowed codepath. The passed buffers are assumed to be
 * of PYI_MESSAGE_LEN size. The functions return the length of message
 * prefix, which allows the prefix to be skipped in the error dialogs
 * (while having it included in message passed to OutputDebugString). */
static int
_pyi_format_message_utf8(char *message_buffer, const char *severity, const char *fmt, va_list args)
{
    char *msg_ptr = message_buffer;
    int buflen = PYI_MESSAGE_LEN;
    int prefix_len = 0;
    int ret;

    /* Prefix: [PYI-{PID}:{SEVERITY}]. */
    ret = snprintf(msg_ptr, buflen, "[PYI-%d:%s] ", _getpid(), severity);
    if (ret >= 0) {
        msg_ptr += ret;
        buflen -= ret;
        if (buflen < 0) {
            buflen = 0;
        }
        prefix_len = ret; /* Store prefix length so we can return it */
    }

    /* Formatted message */
    vsnprintf(msg_ptr, buflen, fmt, args);

    return prefix_len;
}

static int
_pyi_format_message_w(wchar_t *message_buffer, const wchar_t *severity, const wchar_t *fmt, va_list args)
{
    wchar_t *msg_ptr = message_buffer;
    int buflen = PYI_MESSAGE_LEN;
    int prefix_len = 0;
    int ret;

    /* Prefix: [PYI-{PID}:{SEVERITY}]. */
    ret = _snwprintf(msg_ptr, buflen, L"[PYI-%d:%ls] ", _getpid(), severity);
    if (ret >= 0) {
        msg_ptr += ret;
        buflen -= ret;
        if (buflen < 0) {
            buflen = 0;
        }
        prefix_len = ret; /* Store prefix length so we can return it */
    }

    /* Formatted message */
    _vsnwprintf(msg_ptr, buflen, fmt, args);

    return prefix_len;
}

static int
_pyi_format_perror_message_utf8(char *message_buffer, const char *funcname, int error_code, const char *fmt, va_list args)
{
    char *msg_ptr = message_buffer;
    int buflen = PYI_MESSAGE_LEN;
    int prefix_len = 0;
    int ret;

    /* Prefix: [PYI-{PID}:{SEVERITY}]. */
    ret = snprintf(msg_ptr, buflen, "[PYI-%d:ERROR] ", _getpid());
    if (ret >= 0) {
        msg_ptr += ret;
        buflen -= ret;
        if (buflen < 0) {
            buflen = 0;
        }
        prefix_len = ret; /* Store prefix length so we can return it */
    }

    /* Formatted message */
    ret = vsnprintf(msg_ptr, buflen, fmt, args);
    if (ret >= 0) {
        msg_ptr += ret;
        buflen -= ret;
        if (buflen < 0) {
            buflen = 0;
        }
    }

    /* Function name and error message (perror equivalent) */
    snprintf(msg_ptr, buflen, "%s: %s\n", funcname, strerror(error_code));

    return prefix_len;
}

static int
_pyi_format_perror_message_w(wchar_t *message_buffer, const wchar_t *funcname, int error_code, const wchar_t *fmt, va_list args)
{
    wchar_t *msg_ptr = message_buffer;
    int buflen = PYI_MESSAGE_LEN;
    int prefix_len = 0;
    int ret;

    /* Prefix: [PYI-{PID}:{SEVERITY}]. */
    ret = _snwprintf(msg_ptr, buflen, L"[PYI-%d:ERROR] ", _getpid());
    if (ret >= 0) {
        msg_ptr += ret;
        buflen -= ret;
        if (buflen < 0) {
            buflen = 0;
        }
        prefix_len = ret; /* Store prefix length so we can return it */
    }

    /* Formatted message */
    ret = _vsnwprintf(msg_ptr, buflen, fmt, args);
    if (ret >= 0) {
        msg_ptr += ret;
        buflen -= ret;
        if (buflen < 0) {
            buflen = 0;
        }
    }

    /* Function name and error message (perror equivalent) */
    _snwprintf(msg_ptr, buflen, L"%ls: %ls\n", funcname, _wcserror(error_code));

    return prefix_len;
}

static int
_pyi_format_winerror_message_w(wchar_t *message_buffer, const wchar_t *funcname, DWORD error_code, const wchar_t *fmt, va_list args)
{
    wchar_t *msg_ptr = message_buffer;
    int buflen = PYI_MESSAGE_LEN;
    int prefix_len = 0;
    int ret;

    /* Prefix: [PYI-{PID}:{SEVERITY}]. */
    ret = _snwprintf(msg_ptr, buflen, L"[PYI-%d:ERROR] ", _getpid());
    if (ret >= 0) {
        msg_ptr += ret;
        buflen -= ret;
        if (buflen < 0) {
            buflen = 0;
        }
        prefix_len = ret; /* Store prefix length so we can return it */
    }

    /* Formatted message */
    ret = _vsnwprintf(msg_ptr, buflen, fmt, args);
    if (ret >= 0) {
        msg_ptr += ret;
        buflen -= ret;
        if (buflen < 0) {
            buflen = 0;
        }
    }

    /* Function name and error message*/
    ret = _snwprintf(msg_ptr, buflen, L"%ls: ", funcname);
    if (ret >= 0) {
        msg_ptr += ret;
        buflen -= ret;
        if (buflen < 0) {
            buflen = 0;
        }
    }

    /* Note: Giving 0 to dwLanguageID means MAKELANGID(LANG_NEUTRAL,
     * SUBLANG_NEUTRAL), but we should use SUBLANG_DEFAULT instead of
     * SUBLANG_NEUTRAL. Please see the note written in "Language
     * Identifier Constants and Strings" on MSDN.
     * https://docs.microsoft.com/en-us/windows/desktop/intl/language-identifier-constants-and-strings
     */
    ret = FormatMessageW(
        FORMAT_MESSAGE_FROM_SYSTEM, /* dwFlags */
        NULL, /* lpSource */
        error_code, /* dwMessageId */
        MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT), /* dwLanguageId */
        msg_ptr, /* lpBuffer */
        buflen, /* nSize */
        NULL /* Arguments */
    );
    if (ret == 0) {
        _snwprintf(msg_ptr, buflen, L"<FormatMessageW failed.>\n");
    }

    return prefix_len;
}


#if defined(WINDOWED)

/*
 * Implementation used in Windows windowed/noconsole builds. Errors and
 * warnings are signaled via dialogs (as well as written to OutputDebugString
 * in debug-enabled builds). In debug-enabled builds, debug messages are
 * written to OutputDebugString.
 */

/*
 * Narrow-char/UTF-8 version of functions.
 */

/* Helper used by functions that display dialog */
static void
_pyi_output_message_utf8(const char *message_buffer_utf8, int prefix_length, const wchar_t *caption, const char *fallback_caption, UINT icon_type)
{
    wchar_t message_buffer[PYI_MESSAGE_LEN];

    /* Convert UTF-8 message to wide-char */
    if (pyi_win32_utf8_to_wcs(message_buffer_utf8, message_buffer, PYI_MESSAGE_LEN)) {
        /* In debug-enabled builds, submit a copy via OutputDebugString */
#if defined(LAUNCH_DEBUG)
        OutputDebugStringW(message_buffer);
#endif

        /* Show dialog */
        /* NOTE: here, we implicitly assume that the prefix length that
         * was computed on UTF-8 buffer is also valid for the wide-char
         * buffer. Which should be the case, as prefix should contain
         * only ASCII characters. */
        MessageBoxW(NULL, message_buffer + prefix_length, caption, MB_OK | icon_type);
    } else {
        /* Conversion failed; try displaying the original UTF-8 string
         * via the ANSI method. This will produce garbled text if Unicode
         * characters are present, but it is better than nothing. */

        /* In debug-enabled builds, submit a copy via OutputDebugString */
#if defined(LAUNCH_DEBUG)
        OutputDebugStringA(message_buffer_utf8);
#endif

        /* Show dialog */
        MessageBoxA(NULL, message_buffer_utf8 + prefix_length, fallback_caption, MB_OK | icon_type);
    }
}

/* Used by PYI_DEBUG macro. */
#if defined(LAUNCH_DEBUG)

void
pyi_debug_message(const char *fmt, ...)
{
    char message_buffer_utf8[PYI_MESSAGE_LEN];
    wchar_t message_buffer[PYI_MESSAGE_LEN];
    va_list args;

    va_start(args, fmt);
    _pyi_format_message_utf8(message_buffer_utf8, "DEBUG", fmt, args);
    va_end(args);

    /* Convert UTF-8 message to wide-char */
    if (pyi_win32_utf8_to_wcs(message_buffer_utf8, message_buffer, PYI_MESSAGE_LEN)) {
        OutputDebugStringW(message_buffer);
    } else {
        /* Conversion failed; try displaying the original UTF-8 string
         * via the ANSI method. This will produce garbled text if Unicode
         * characters are present, but it is better than nothing. */
        OutputDebugStringA(message_buffer_utf8);
    }
}

#endif

void
pyi_warning_message(const char *fmt, ...)
{
    char message_buffer[PYI_MESSAGE_LEN];
    int prefix_length;
    va_list args;

    va_start(args, fmt);
    prefix_length = _pyi_format_message_utf8(message_buffer, "WARNING", fmt, args);
    va_end(args);

    _pyi_output_message_utf8(message_buffer, prefix_length, L"Warning", "Warning [ANSI Fallback]", MB_ICONWARNING);
}


void
pyi_error_message(const char *fmt, ...)
{
    char message_buffer[PYI_MESSAGE_LEN];
    int prefix_length;
    va_list args;

    va_start(args, fmt);
    prefix_length = _pyi_format_message_utf8(message_buffer, "ERROR", fmt, args);
    va_end(args);

    _pyi_output_message_utf8(message_buffer, prefix_length, L"Error", "Error [ANSI Fallback]", MB_ICONERROR);
}

void
pyi_perror_message(const char *funcname, int error_code, const char *fmt, ...)
{
    char message_buffer[PYI_MESSAGE_LEN];
    int prefix_length;
    va_list args;

    va_start(args, fmt);
    prefix_length = _pyi_format_perror_message_utf8(message_buffer, funcname, error_code, fmt, args);
    va_end(args);

    _pyi_output_message_utf8(message_buffer, prefix_length, L"Error", "Error [ANSI Fallback]", MB_ICONERROR);
}

/*
 * Native wide-char version of functions.
 */

/* Used by PYI_DEBUG_W macro. */
#if defined(LAUNCH_DEBUG)

void
pyi_debug_message_w(const wchar_t *fmt, ...)
{
    wchar_t message_buffer[PYI_MESSAGE_LEN];
    va_list args;

    va_start(args, fmt);
    _pyi_format_message_w(message_buffer, L"DEBUG", fmt, args);
    va_end(args);

    OutputDebugStringW(message_buffer);
}

#endif

/* Used by PYI_WARNING_W macro. */
void
pyi_warning_message_w(const wchar_t *fmt, ...)
{
    wchar_t message_buffer[PYI_MESSAGE_LEN];
    int prefix_length;
    va_list args;

    va_start(args, fmt);
    prefix_length = _pyi_format_message_w(message_buffer, L"WARNING", fmt, args);
    va_end(args);

#if defined(LAUNCH_DEBUG)
    OutputDebugStringW(message_buffer);
#endif

    MessageBoxW(NULL, message_buffer + prefix_length, L"Warning", MB_OK | MB_ICONWARNING);
}

/* Used by PYI_ERROR_W macro. */
void
pyi_error_message_w(const wchar_t *fmt, ...)
{
    wchar_t message_buffer[PYI_MESSAGE_LEN];
    int prefix_length;
    va_list args;

    va_start(args, fmt);
    prefix_length = _pyi_format_message_w(message_buffer, L"ERROR", fmt, args);
    va_end(args);

#if defined(LAUNCH_DEBUG)
    OutputDebugStringW(message_buffer);
#endif

    MessageBoxW(NULL, message_buffer + prefix_length, L"Error", MB_OK | MB_ICONERROR);
}

/* Used by PYI_PERROR_W macro. */
void
pyi_perror_message_w(const wchar_t *funcname, int error_code, const wchar_t *fmt, ...)
{
    wchar_t message_buffer[PYI_MESSAGE_LEN];
    int prefix_length;
    va_list args;

    va_start(args, fmt);
    prefix_length = _pyi_format_perror_message_w(message_buffer, funcname, error_code, fmt, args);
    va_end(args);

#if defined(LAUNCH_DEBUG)
    OutputDebugStringW(message_buffer);
#endif

    MessageBoxW(NULL, message_buffer + prefix_length, L"Error", MB_OK | MB_ICONERROR);
}

/* Used by PYI_WINERROR_W macro. */
void
pyi_winerror_message_w(const wchar_t *funcname, DWORD error_code, const wchar_t *fmt, ...)
{
    wchar_t message_buffer[PYI_MESSAGE_LEN];
    int prefix_length;
    va_list args;

    va_start(args, fmt);
    prefix_length = _pyi_format_winerror_message_w(message_buffer, funcname, error_code, fmt, args);
    va_end(args);

#if defined(LAUNCH_DEBUG)
    OutputDebugStringW(message_buffer);
#endif

    MessageBoxW(NULL, message_buffer + prefix_length, L"Error", MB_OK | MB_ICONERROR);
}


#else /* defined(WINDOWED) */

/*
 * Implementation used in Windows noconsole builds. All messages are
 * written to stderr. In debug-enabled builds, a copy of each message
 * is also written to OutputDebugString.
 */

/*
 * Narrow-char/UTF-8 version of functions.
 */
static void
_pyi_output_message_utf8(const char *message_buffer_utf8)
{
    wchar_t message_buffer[PYI_MESSAGE_LEN];

    /* Convert UTF-8 message to wide-char */
    if (pyi_win32_utf8_to_wcs(message_buffer_utf8, message_buffer, PYI_MESSAGE_LEN)) {
        /* Write to stderr */
        fwprintf(stderr, L"%ls", message_buffer);

        /* In debug-enabled builds, also submit a copy via OutputDebugString */
#if defined(LAUNCH_DEBUG)
        OutputDebugStringW(message_buffer);
#endif
    } else {
        /* Conversion failed; try displaying the original UTF-8 string
         * via the ANSI method. This will produce garbled text if Unicode
         * characters are present, but it is better than nothing. Also,
         * we should not be mixing ANSI and wide-char I/O, although
         * Windows seems to be quite forgiving in this regard (i.e.,
         * stream orientation does not seem to matter). */

         /* Write to stderr */
        fprintf(stderr, "%s [ANSI fallback]", message_buffer_utf8);

        /* In debug-enabled builds, also submit a copy via OutputDebugString */
#if defined(LAUNCH_DEBUG)
        OutputDebugStringA(message_buffer_utf8);
#endif
    }
}

/* Print a formatted debug/warning/error message to stderr. The message
 * is formatted in UTF-8, then converted to wide-char and written to stderr
 * using fwprintf(). */

/* Used by PYI_DEBUG macro. */
#if defined(LAUNCH_DEBUG)

void pyi_debug_message(const char *fmt, ...)
{
    char message_buffer[PYI_MESSAGE_LEN];
    va_list args;

    va_start(args, fmt);
    _pyi_format_message_utf8(message_buffer, "DEBUG", fmt, args);
    va_end(args);

    _pyi_output_message_utf8(message_buffer);
}

#endif /* defined(LAUNCH_DEBUG) */

/* Used by PYI_WARNING macro. */
void pyi_warning_message(const char *fmt, ...)
{
    char message_buffer[PYI_MESSAGE_LEN];
    va_list args;

    va_start(args, fmt);
    _pyi_format_message_utf8(message_buffer, "WARNING", fmt, args);
    va_end(args);

    _pyi_output_message_utf8(message_buffer);
}

/* Used by PYI_ERROR macro. */
void pyi_error_message(const char *fmt, ...)
{
    char message_buffer[PYI_MESSAGE_LEN];
    va_list args;

    va_start(args, fmt);
    _pyi_format_message_utf8(message_buffer, "ERROR", fmt, args);
    va_end(args);

    _pyi_output_message_utf8(message_buffer);
}

/* Print a formatted message, followed by the name of the function that
 * resulted in an error and a textual description of the error, obtained
 * via strerror(). Used by PYI_PERROR macro. */
void
pyi_perror_message(const char *funcname, int error_code, const char *fmt, ...)
{
    char message_buffer[PYI_MESSAGE_LEN];
    va_list args;

    va_start(args, fmt);
    _pyi_format_perror_message_utf8(message_buffer, funcname, error_code, fmt, args);
    va_end(args);

    _pyi_output_message_utf8(message_buffer);
}


/*
 * Native wide-char version of functions.
 */
static void
_pyi_output_message_w(const wchar_t *message_buffer)
{
    /* Write to stderr */
    fwprintf(stderr, L"%ls", message_buffer);

    /* In debug-enabled builds, also submit a copy via OutputDebugString */
#if defined(LAUNCH_DEBUG)
    OutputDebugStringW(message_buffer);
#endif
}

/* Used by PYI_DEBUG_W macro. */
#if defined(LAUNCH_DEBUG)

void pyi_debug_message_w(const wchar_t *fmt, ...)
{
    wchar_t message_buffer[PYI_MESSAGE_LEN];
    va_list args;

    va_start(args, fmt);
    _pyi_format_message_w(message_buffer, L"DEBUG", fmt, args);
    va_end(args);

    _pyi_output_message_w(message_buffer);
}

#endif /* defined(LAUNCH_DEBUG) */

/* Used by PYI_WARNING_W macro. */
void pyi_warning_message_w(const wchar_t *fmt, ...)
{
    wchar_t message_buffer[PYI_MESSAGE_LEN];
    va_list args;

    va_start(args, fmt);
    _pyi_format_message_w(message_buffer, L"WARNING", fmt, args);
    va_end(args);

    _pyi_output_message_w(message_buffer);
}

/* Used by PYI_ERROR macro. */
void pyi_error_message_w(const wchar_t *fmt, ...)
{
    wchar_t message_buffer[PYI_MESSAGE_LEN];
    va_list args;

    va_start(args, fmt);
    _pyi_format_message_w(message_buffer, L"ERROR", fmt, args);
    va_end(args);

    _pyi_output_message_w(message_buffer);
}


/* Print a formatted message, followed by the name of the function that
 * resulted in an error and a textual description of the error, obtained
 * via _wcserror(). Used by PYI_PERROR_W macro. */
void
pyi_perror_message_w(const wchar_t *funcname, int error_code, const wchar_t *fmt, ...)
{
    wchar_t message_buffer[PYI_MESSAGE_LEN];
    va_list args;

    va_start(args, fmt);
    _pyi_format_perror_message_w(message_buffer, funcname, error_code, fmt, args);
    va_end(args);

    _pyi_output_message_w(message_buffer);
}


/* Print a formatted message, followed by the name of the function that
 * resulted in an error and a textual description of the error, obtained
 * via FormatMessage() win32 API. Used by PYI_WINERROR_W macro. */
void
pyi_winerror_message_w(const wchar_t *funcname, DWORD error_code, const wchar_t *fmt, ...)
{
    wchar_t message_buffer[PYI_MESSAGE_LEN];
    va_list args;

    va_start(args, fmt);
    _pyi_format_winerror_message_w(message_buffer, funcname, error_code, fmt, args);
    va_end(args);

    _pyi_output_message_w(message_buffer);
}


#endif  /* defined(WINDOWED) */

#endif /* ifdef(_WIN32) */
