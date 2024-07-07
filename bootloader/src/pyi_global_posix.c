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
 * contains implementations that are specific to POSIX platforms.
 */

/* Having a header included outside of the ifdef block prevents the compilation
 * unit from becoming empty, which is disallowed by pedantic ISO C. */
#include "pyi_global.h"

#ifndef _WIN32

#include <stdio.h>
#include <stdarg.h> /* va_list, va_start(), va_end() */
#include <unistd.h> /* getpid() */
#include <string.h> /* strerror() */
#include <sys/types.h>

/* On macOS, have windowed bootloader also send messages to syslog. */
#if defined(__APPLE__) && defined(WINDOWED)
#include <syslog.h>
#endif

/* PyInstaller headers. */
#include "pyi_utils.h"


/**********************************************************************\
 *               Debug and error message implementation               *
\**********************************************************************/
/* On POSIX platforms, these are relatively straight-forward.
 *
 * We have console available, so print messages to stderr.
 *
 * In macOS .app bundle bootloaders, also send a copy of message to syslog.
 * This allows user to see bootloader debug messages in the Console.app
 * log viewer: https://en.wikipedia.org/wiki/Console_(OS_X)
 * Levels DEBUG and INFO seem to be ignored, so use level NOTICE.
 */

/* Maximum length of debug/warning/error messages */
#define PYI_MESSAGE_LEN 4096


/* Print a formatted debug/warning/error message to stderr. */
static void
_pyi_debug_printf(const char *severity, const char *fmt, va_list args)
{
    char message_buffer[PYI_MESSAGE_LEN]; /* Local buffer to ensure thread-safety! */
    char *msg_ptr = message_buffer;
    int buflen = PYI_MESSAGE_LEN;
    int ret;

    /* Prefix: [PYI-{PID}:{SEVERITY}]. */
    ret = snprintf(msg_ptr, buflen, "[PYI-%d:%s] ", getpid(), severity);
    if (ret >= 0) {
        msg_ptr += ret;
        buflen -= ret;
        if (buflen < 0) {
            buflen = 0;
        }
    }

    /* Formatted message */
    vsnprintf(msg_ptr, buflen, fmt, args);

    /* Write to stderr */
    fprintf(stderr, "%s", message_buffer);

    /* Write to syslog */
#if defined(__APPLE__) && defined(WINDOWED)
    syslog(LOG_NOTICE, "%s", message_buffer);
#endif
}


/* Used by PYI_DEBUG macro. */
#if defined(LAUNCH_DEBUG)

void pyi_debug_message(const char *fmt, ...)
{
    va_list args;
    va_start(args, fmt);
    _pyi_debug_printf("DEBUG", fmt, args);
    va_end(args);
}

#endif /* defined(LAUNCH_DEBUG) */

/* Used by PYI_WARNING macro. */
void pyi_warning_message(const char *fmt, ...)
{
    va_list args;
    va_start(args, fmt);
    _pyi_debug_printf("WARNING", fmt, args);
    va_end(args);
}

/* Used by PYI_ERROR macro. */
void pyi_error_message(const char *fmt, ...)
{
    va_list args;
    va_start(args, fmt);
    _pyi_debug_printf("ERROR", fmt, args);
    va_end(args);
}


/* Print a formatted message, followed by the name of the function that
 * resulted in an error and a textual description of the error, obtained
 * via strerror(). Used by PYI_PERROR macro. */
void
pyi_perror_message(const char *funcname, int error_code, const char *fmt, ...)
{
    char message_buffer[PYI_MESSAGE_LEN]; /* Local buffer to ensure thread-safety! */
    char *msg_ptr = message_buffer;
    int buflen = PYI_MESSAGE_LEN;
    int ret;

    va_list args;

    /* Prefix: [PYI-{PID}:{SEVERITY}]. */
    ret = snprintf(msg_ptr, buflen, "[PYI-%d:ERROR] ", getpid());
    if (ret >= 0) {
        msg_ptr += ret;
        buflen -= ret;
        if (buflen < 0) {
            buflen = 0;
        }
    }

    /* Formatted message */
    va_start(args, fmt);
    ret = vsnprintf(msg_ptr, buflen, fmt, args);
    va_end(args);

    if (ret >= 0) {
        msg_ptr += ret;
        buflen -= ret;
        if (buflen < 0) {
            buflen = 0;
        }
    }

    /* Function name and error message (perror equivalent) */
    snprintf(msg_ptr, buflen, "%s: %s\n", funcname, strerror(error_code));

    /* Write to stderr */
    fprintf(stderr, "%s", message_buffer);

    /* Write to syslog */
#if defined(__APPLE__) && defined(WINDOWED)
    syslog(LOG_NOTICE, "%s", message_buffer);
#endif
}


#endif /* ifndef(_WIN32) */
