/*
 * ****************************************************************************
 * Copyright (c) 2013-2016, PyInstaller Development Team.
 * Distributed under the terms of the GNU General Public License with exception
 * for distributing bootloader.
 *
 * The full license is in the file COPYING.txt, distributed with this software.
 * ****************************************************************************
 */

/*
 * Glogal shared fuctions used in many bootloader files.
 */

/*
 * Enable use of Sean's Tool Box -- public domain -- http://nothings.org/stb.h.
 * File stb.h.
 * All functions starting with 'stb_' prefix are from this toolbox.
 *
 * This define has to be only in one C source file!
 */
/* #define STB_DEFINE  1/ * * / */
/* #define STB_NO_REGISTRY 1 / * No need for Windows registry functions in stb.h. * / */

/* TODO: use safe string functions */
#define _CRT_SECURE_NO_WARNINGS 1

#include <stdarg.h>  /* va_list, va_start(), va_end() */
#include <stdio.h>

#ifdef _WIN32
    #include <windows.h>
    #include <direct.h>
    #include <process.h>
    #include <io.h>
#endif

/* On Mac OS X send debug msg also to syslog for gui app in debug mode. */
#if defined(__APPLE__) && defined(WINDOWED) && defined(LAUNCH_DEBUG)
    #include <syslog.h>
#endif

/* PyInstaller headers. */
#include "pyi_global.h"

/* Text length of MessageBox(). */
#define MBTXTLEN 1024

/* Locale is saved at the start of main(), and restored immediately before running
 * scripts in pyi_launch_run_scripts
 */
char *saved_locale;

/*
 * On Windows and with windowed mode (no console) show error messages
 * in message boxes. In windowed mode nothing is written to console.
 */

#if defined(_WIN32) && defined(WINDOWED)
void
mbfatalerror(const char *fmt, ...)
{
    char msg[MBTXTLEN];
    va_list args;

    va_start(args, fmt);
    vsnprintf(msg, MBTXTLEN, fmt, args);
    va_end(args);

    MessageBoxA(NULL, msg, "Fatal Error!", MB_OK | MB_ICONEXCLAMATION);
}

void
mbothererror(const char *fmt, ...)
{
    char msg[MBTXTLEN];
    va_list args;

    va_start(args, fmt);
    vsnprintf(msg, MBTXTLEN, fmt, args);
    va_end(args);

    MessageBoxA(NULL, msg, "Error!", MB_OK | MB_ICONWARNING);
}
#endif  /* _WIN32 and WINDOWED */

/* Enable or disable debug output. */

#ifdef LAUNCH_DEBUG
    #if defined(_WIN32) && defined(WINDOWED)
void
mbvs(const char *fmt, ...)
{
    char msg[MBTXTLEN];
    va_list args;

    va_start(args, fmt);
    vsnprintf(msg, MBTXTLEN, fmt, args);
    /* Ensure message is trimmed to fit the buffer. */
    /* msg[MBTXTLEN-1] = '\0'; */
    va_end(args);

    MessageBoxA(NULL, msg, "Tracing", MB_OK);
}
    #endif /* if defined(_WIN32) && defined(WINDOWED) */
#endif /* ifdef LAUNCH_DEBUG */

/* TODO improve following for windows. */
/*
 * Wrap printing debug messages to console.
 */
void
pyi_global_printf(const char *fmt, ...)
{
    va_list v;

    va_start(v, fmt);
    /* Sent 'LOADER text' messages to stderr. */
    vfprintf(stderr, fmt, v);
    va_end(v);
    /* For Gui apps on Mac OS X send debug messages also to syslog. */
    /* This allows to see bootloader debug messages in the Console.app log viewer. */
    /* https://en.wikipedia.org/wiki/Console_(OS_X) */
    /* Levels DEBUG and INFO are ignored so use level NOTICE. */
#if defined(__APPLE__) && defined(WINDOWED) && defined(LAUNCH_DEBUG)
    va_start(v, fmt);
    vsyslog(LOG_NOTICE, fmt, v);
    va_end(v);
#endif
}
