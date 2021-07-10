/*
 * ****************************************************************************
 * Copyright (c) 2013-2021, PyInstaller Development Team.
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
    #include <windows.h>  /* HINSTANCE */
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
    #include <limits.h>
    #define PATH_MAX 1024  /* Recommended value for OSX. */
#else
    #include <limits.h>  /* PATH_MAX */
#endif

/*
 * These macros used to define variables to hold dynamically accessed entry
 * points. These are declared 'extern' in the header, and defined fully later.
 */
#ifdef _WIN32

    #define EXTDECLPROC(result, name, args) \
    typedef result (__cdecl *__PROC__ ## name) args; \
    extern __PROC__ ## name PI_ ## name;

    #define EXTDECLVAR(vartyp, name) \
    typedef vartyp __VAR__ ## name; \
    extern __VAR__ ## name *PI_ ## name;

#else

    #define EXTDECLPROC(result, name, args) \
    typedef result (*__PROC__ ## name) args; \
    extern __PROC__ ## name PI_ ## name;

    #define EXTDECLVAR(vartyp, name) \
    typedef vartyp __VAR__ ## name; \
    extern __VAR__ ## name *PI_ ## name;

#endif  /* WIN32 */

/* Macros to declare and get foreign entry points in the C file.
 * Typedefs '__PROC__...' have been done above
 *
 * GETPROC_RENAMED is to support APIs functions that are simply renamed. We use
 * the new name, and when loading an old Python lib, load the old symbol into the
 * new name.
 */
#ifdef _WIN32

    #define DECLPROC(name) \
    __PROC__ ## name PI_ ## name = NULL;
    #define GETPROCOPT(dll, name, sym) \
    PI_ ## name = (__PROC__ ## name)GetProcAddress (dll, #sym)
    #define GETPROC(dll, name) \
    GETPROCOPT(dll, name, name); \
    if (!PI_ ## name) { \
        FATAL_WINERROR("GetProcAddress", "Failed to get address for " #name "\n"); \
        return -1; \
    }
    #define GETPROC_RENAMED(dll, name, sym) \
    GETPROCOPT(dll, name, sym); \
    if (!PI_ ## name) { \
        FATAL_WINERROR("GetProcAddress", "Failed to get address for " #sym "\n"); \
        return -1; \
    }
    #define DECLVAR(name) \
    __VAR__ ## name * PI_ ## name = NULL;
    #define GETVAR(dll, name) \
    PI_ ## name = (__VAR__ ## name *)GetProcAddress (dll, #name); \
    if (!PI_ ## name) { \
        FATAL_WINERROR("GetProcAddress", "Failed to get address for " #name "\n"); \
        return -1; \
    }

#else  /* ifdef _WIN32 */

    #define DECLPROC(name) \
    __PROC__ ## name PI_ ## name = NULL;
    #define GETPROCOPT(dll, name, sym) \
    PI_ ## name = (__PROC__ ## name)dlsym (dll, #sym)
    #define GETPROC(dll, name) \
    GETPROCOPT(dll, name, name); \
    if (!PI_ ## name) { \
        FATALERROR ("Cannot dlsym for " #name "\n"); \
        return -1; \
    }
    #define GETPROC_RENAMED(dll, name, sym) \
    GETPROCOPT(dll, name, sym); \
    if (!PI_ ## name) { \
        FATALERROR ("Cannot dlsym for " #sym "\n"); \
        return -1; \
    }
    #define DECLVAR(name) \
    __VAR__ ## name * PI_ ## name = NULL;
    #define GETVAR(dll, name) \
    PI_ ## name = (__VAR__ ## name *)dlsym(dll, #name); \
    if (!PI_ ## name) { \
        FATALERROR ("Cannot dlsym for " #name "\n"); \
        return -1; \
    }

#endif  /* WIN32 */

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
 * in message boxes. In windowed mode nothing is written to console.
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
        /* Don't have console, resort to debugger output */
        #define VS mbvs
void mbvs(const char *fmt, ...);
    #else
        /* Have console, printf works */
        #define VS pyi_global_printf
    #endif
#else
    #if defined(_WIN32) && defined(_MSC_VER)
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
    #define PYI_CURDIRSTR  "."
#else
    #define PYI_PATHSEP    ':'
    #define PYI_CURDIR     '.'
    #define PYI_SEP        '/'
    #define PYI_SEPSTR     "/"
    #define PYI_PATHSEPSTR ":"
    #define PYI_CURDIRSTR  "."
#endif

/* Strings are usually terminated by this character. */
#define PYI_NULLCHAR       '\0'

/* File seek and tell with large (64-bit) offsets */
#if defined(_WIN32) && defined(_MSC_VER)
    #define pyi_fseek _fseeki64
    #define pyi_ftell _ftelli64
#else
    #define pyi_fseek fseeko
    #define pyi_ftell ftello
#endif

/* Byte-order conversion macros */
#ifdef _WIN32
    /* On Windows, use compiler specific functions/macros to avoid
     * using ntohl(), which requires linking against ws2 library. */
    #if BYTE_ORDER == LITTLE_ENDIAN
        #if defined(_MSC_VER)
            #include <stdlib.h>  /* _byteswap_ulong */
            #define pyi_be32toh(x) _byteswap_ulong(x)
        #elif defined(__GNUC__) || defined(__clang__)
            #define pyi_be32toh(x) __builtin_bswap32(x)
        #else
            #error Unsupported compiler
        #endif
    #elif BYTE_ORDER == BIG_ENDIAN
        #define pyi_be32toh(x) (x)
    #else
        #error Unsupported byte order
    #endif
#else
    /* On all non-Windows platforms, use ntohl() */
    #ifdef __FreeBSD__
        /* freebsd issue #188316 */
        #include <arpa/inet.h>  /* ntohl */
    #else
        #include <netinet/in.h>  /* ntohl */
    #endif
    #define pyi_be32toh(x) ntohl(x)
#endif /* ifdef _WIN32 */

/* Saved LC_CTYPE locale */
extern char *saved_locale;

#endif  /* PYI_GLOBAL_H */
