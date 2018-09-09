/*
 * ****************************************************************************
 * Copyright (c) 2013-2018, PyInstaller Development Team.
 * Distributed under the terms of the GNU General Public License with exception
 * for distributing bootloader.
 *
 * The full license is in the file COPYING.txt, distributed with this software.
 * ****************************************************************************
 */

/*
 * Global shared declarations used in many bootloader files.
 */

#ifndef PYI_GLOBAL_H
#define PYI_GLOBAL_H

/*
 * Detect memory leaks.
 *
 * Use Boehm garbage collector to detect memory leaks.
 * malloc(), free(), strdup() and similar functions
 * are replaced by calls from the gc library.
 */
#ifdef PYI_LEAK_DETECTOR
    #include <gc/leak_detector.h>
#endif

/*
 * Definition of type boolean. On OSX boolean type is available
 * in header <stdbool.h>.
 */
#ifdef __APPLE__
    #include <stdbool.h>  /* bool, true, false */
#else
/*
 * It looks like more recent versions of MSVC complains about 'typedef int bool'.
 * They probably have the type 'bool' defined.
 * TODO find out more info.
 */
    #undef bool
    #undef true
    #undef false
typedef int bool;
    #define true    1
    #define false   0
#endif

/* Type for dynamic library. */
#ifdef _WIN32
    #define dylib_t   HINSTANCE
#else
    #define dylib_t   void *
#endif

/* Wrap some windows specific declarations for Unix. */
#ifndef _WIN32
    #define HMODULE void *
#endif

/*
 * On Windows PATH_MAX does not exist but MAX_PATH does.
 * WinAPI MAX_PATH limit is only 256. MSVCR fuctions does not have this limit.
 * Redefine PATH_MAX for Windows to support longer path names.
 */
/* TODO use MSVCR function for file path handling. */
#ifdef _WIN32
    #ifdef PATH_MAX
        #undef PATH_MAX  /* On Windows override PATH_MAX if defined. */
    #endif
    #define PATH_MAX 4096  /* Default value on Linux. */
#elif __APPLE__
    #define PATH_MAX 1024  /* Recommended value for OSX. */
#endif

/*
 * Debug and error macros.
 */

void pyi_global_printf(const char *fmt, ...);
void pyi_global_perror(const char *funcname, const char *fmt, ...);
#ifdef _WIN32
    void pyi_global_winerror(const char *funcname, const char *fmt, ...);
#endif
/*
 * On Windows and with windowed mode (no console) show error messages
 * in message boxes. In windowed mode nothing might be written to console.
 */

#if defined(_WIN32) && defined(WINDOWED)
void mbfatalerror(const char *fmt, ...);
    #define FATALERROR mbfatalerror

void mbothererror(const char *fmt, ...);
    #define OTHERERROR mbothererror

    void mbfatal_perror(const char *funcname, const char *fmt, ...);
    #define FATAL_PERROR mbfatal_perror

    void mbfatal_winerror(const char *funcname, const char *fmt, ...);
    #define FATAL_WINERROR mbfatal_winerror

#else
/* TODO copy over stbprint to bootloader. */
    #define FATALERROR pyi_global_printf
    #define OTHERERROR pyi_global_printf
    #define FATAL_PERROR pyi_global_perror
    #define FATAL_WINERROR pyi_global_winerror
#endif  /* WIN32 and WINDOWED */

/* Enable or disable debug output. */

#ifdef LAUNCH_DEBUG
    #if defined(_WIN32) && defined(WINDOWED)
        #define VS mbvs
void mbvs(const char *fmt, ...);
    #else
        #define VS pyi_global_printf
    #endif
#else
    #ifdef _WIN32
        #define VS
    #else
        #define VS(...)
    #endif
#endif

/* Path and string macros. */

#ifdef _WIN32
    #define PYI_PATHSEP    ';'
    #define PYI_CURDIR     '.'
    #define PYI_SEP        '\\'
/*
 * For some functions like strcat() we need to pass
 * string and not only char.
 */
    #define PYI_SEPSTR     "\\"
    #define PYI_PATHSEPSTR ";"
#else
    #define PYI_PATHSEP    ':'
    #define PYI_CURDIR     '.'
    #define PYI_SEP        '/'
    #define PYI_SEPSTR     "/"
    #define PYI_PATHSEPSTR ":"
#endif

/* Strings are usually terminated by this character. */
#define PYI_NULLCHAR       '\0'

/* Rewrite ANSI/POSIX functions to Win32 equivalents. */
#if defined(_WIN32) && defined(_MSC_VER)
    #define getpid           _getpid
    #define mkdir            _mkdir
    #define rmdir            _rmdir
    #define snprintf         _snprintf
    #define stat             _stat
    #define strdup           _strdup
    #define vsnprintf        _vsnprintf
/*
 * Mingw on Windows contains the following functions.
 * Redefine them only if they are not available.
 */
    #ifndef fileno
        #define fileno           _fileno
    #endif
#endif

/* Saved LC_CTYPE locale */
extern char *saved_locale;

#endif  /* PYI_GLOBAL_H */
