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

#ifndef _WIN32

#include <stdio.h>
#include <stdarg.h> /* va_list, va_start(), va_end() */
#include <unistd.h> /* getpid() */
#include <sys/types.h>

/* On macOS, have windowed bootloader also send messages to syslog. */
#if defined(__APPLE__) && defined(WINDOWED)
#include <syslog.h>
#endif

/* PyInstaller headers. */
#include "pyi_global.h"
#include "pyi_utils.h"


/**********************************************************************\
 *               Debug and error message implementation               *
\**********************************************************************/
/* On POSIX platforms, these are straight-forward. We have console
 * available, so print messages to stderr. */

/* Print a formatted message. Used by PYI_ERROR and PYI_WARNING macros,
 * and by PYI_DEBUG macro in debug-enabled builds. */
void
pyi_debug_printf(const char *fmt, ...)
{
    va_list v;

    /* Print the [PID] prefix. */
    fprintf(stderr, "[%d] ", getpid());

    /* Print the message */
    va_start(v, fmt);
    vfprintf(stderr, fmt, v);
    va_end(v);

    /* In macOS .app bundle bootloaders, send a copy of debug message
     * to syslog. This allows user to see bootloader debug messages in
     * the Console.app log viewer. */
    /* https://en.wikipedia.org/wiki/Console_(OS_X) */
    /* Levels DEBUG and INFO are ignored so use level NOTICE. */
#if defined(__APPLE__) && defined(WINDOWED)
    va_start(v, fmt);
    vsyslog(LOG_NOTICE, fmt, v);
    va_end(v);
#endif
}

/* Print a formatted message, followed by the name of the function that
 * resulted in an error and a textual description of the error, obtained
 * via strerror(). Used by PYI_PERROR macro. */
void
pyi_debug_perror(const char *funcname, int error_code, const char *fmt, ...)
{
    (void)error_code; /* FIXME: replace perror() call with strerror() */

    va_list v;

    /* Formatted message */
    va_start(v, fmt);
    vfprintf(stderr, fmt, v);
    va_end(v);

    /* Perror-formatted error message */
    perror(funcname); /* perror() writes to stderr */

#if defined(__APPLE__) && defined(WINDOWED)
    va_start(v, fmt);
    vsyslog(LOG_NOTICE, fmt, v);
    vsyslog(LOG_NOTICE, "%m\n", NULL);  /* %m emits the result of strerror() */
    va_end(v);
#endif
}


#endif /* ifndef(_WIN32) */
