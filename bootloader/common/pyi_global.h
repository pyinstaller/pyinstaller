/*
 * ****************************************************************************
 * Copyright (c) 2013, PyInstaller Development Team.
 * Distributed under the terms of the GNU General Public License with exception
 * for distributing bootloader.
 *
 * The full license is in the file COPYING.txt, distributed with this software.
 * ****************************************************************************
 */


/*
 * Glogal shared declarations used in many bootloader files.
 */


#ifndef HEADER_PYI_GLOBAL_H
#define HEADER_PYI_GLOBAL_H


/*
 * Definition of type boolean. On OSX boolean type is available.
 */
typedef int bool_t;

#define false 0
#define true  1


/* Type for dynamic library. */
#ifdef WIN32
#define dylib_t   HINSTANCE
#else
#define dylib_t   void *
#endif

/* Wrap some windows specific declarations for Unix. */
#ifndef WIN32
#define HMODULE void *
#endif


/*
 * On Windows PATH_MAX does not exist but MAX_PATH does.
 * WinAPI MAX_PATH limit is only 256. MSVCR fuctions does not have this limit.
 * Redefine PATH_MAX for Windows to support longer path names.
 */
// TODO use MSVCR function for file path handling.
#ifdef WIN32
    #define PATH_MAX 4096  /* Default value on Linux. */
#endif


/*
 * Debug and error macros.
 */


/*
 * On Windows and with windowed mode (no console) show error messages
 * in message boxes. In windowed mode nothing might be written to console.
 */

#if defined(WIN32) && defined(WINDOWED)
    void mbfatalerror(const char *fmt, ...);
    #define FATALERROR mbfatalerror

    void mbothererror(const char *fmt, ...);
    #define OTHERERROR mbothererror
#else
    #define FATALERROR stbprint
    #define OTHERERROR stbprint
#endif /* WIN32 and WINDOWED */


/* Enable or disable debug output. */

#ifdef LAUNCH_DEBUG
    #if defined(WIN32) && defined(WINDOWED)
        #define VS mbvs
        void mbvs(const char *fmt, ...);
    #else
        #define VS stbprint
    #endif
#else
    #ifdef WIN32
        #define VS
    #else
        #define VS(...)
    #endif
#endif


/* Path separator. */

#ifdef WIN32
    #define PATHSEP ";"
    #define SEP '\\'
#else
    #define PATHSEP ":"
    #define SEP '/'
#endif


/* Rewrite ANSI/POSIX functions to Win32 equivalents. */
#ifdef WIN32
    #define fileno           _fileno
    #define getpid           _getpid
    #define mkdir            _mkdir
    #define rmdir            _rmdir
    #define snprintf         _snprintf
    #define stat             _stat
    #define strdup           _strdup
    #define vsnprintf        _vsnprintf
#endif




/* Refers to 1st item in the archive status_list. */
#define SELF 0

#endif /* HEADER_PYI_GLOBAL_H */
