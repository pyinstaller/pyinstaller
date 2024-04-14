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
 * Global shared declarations used in many bootloader files.
 */

#ifndef PYI_GLOBAL_H
#define PYI_GLOBAL_H

#ifdef _WIN32
    #include <windows.h>
#endif

/* In the unlikely event that stdbool.h is not available, use our own
 * definitions of bool, true, and false. */
#ifdef HAVE_STDBOOL_H
    #include <stdbool.h>
#else
    #define bool int
    #define true 1
    #define false 0
#endif


/* Type for handle to open/loaded dynamic library. */
#ifdef _WIN32
    #define pyi_dylib_t HMODULE
#else
    #define pyi_dylib_t void *
#endif


/* Maximum buffer size for statically allocated path-related buffers in
 * PyInstaller code. */
#ifdef _WIN32
    /* Match the default value of PATH_MAX used on Linux. */
    #define PYI_PATH_MAX 4096
#elif __APPLE__
    /* Recommended value for macOS. */
    #define PYI_PATH_MAX 1024
#else
    /* Use PATH_MAX as defined in limits.h */
    #include <limits.h>
    #define PYI_PATH_MAX PATH_MAX
#endif


/*
 * These macros used to define variables to hold dynamically accessed
 * entry points. These are declared 'extern' in the header, and defined
 * fully later.
 */
#ifdef _WIN32

#define PYI_EXTDECLPROC(result, name, args) \
    typedef result (__cdecl *__PROC__ ## name) args; \
    extern __PROC__ ## name PI_ ## name;

#else /* ifdef _WIN32 */

#define PYI_EXTDECLPROC(result, name, args) \
    typedef result (*__PROC__ ## name) args; \
    extern __PROC__ ## name PI_ ## name;

#endif  /* ifdef _WIN32 */


/*
 * Macros to declare and bind foreign entry points in the C file.
 * Typedefs '__PROC__...' have been done above
 */
#ifdef _WIN32

#define PYI_DECLPROC(name) \
    __PROC__ ## name PI_ ## name = NULL;

#define PYI_GETPROCOPT(dll, name, sym) \
    PI_ ## name = (__PROC__ ## name)GetProcAddress (dll, #sym)

#define PYI_GETPROC(dll, name) \
    PYI_GETPROCOPT(dll, name, name); \
    if (!PI_ ## name) { \
        PYI_WINERROR("GetProcAddress", "Failed to get address for " #name "\n"); \
        return -1; \
    }

#else /* ifdef _WIN32 */

#define PYI_DECLPROC(name) \
    __PROC__ ## name PI_ ## name = NULL;

#define PYI_GETPROCOPT(dll, name, sym) \
    PI_ ## name = (__PROC__ ## name)dlsym (dll, #sym)

#define PYI_GETPROC(dll, name) \
    PYI_GETPROCOPT(dll, name, name); \
    if (!PI_ ## name) { \
        PYI_ERROR("Cannot dlsym for " #name "\n"); \
        return -1; \
    }

#endif /* ifdef _WIN32 */


/*
 * Debug and error macros.
 */

#if defined(_WIN32) && defined(WINDOWED)

/* On Windows in windowed/noconsole mode, we display error messages via
 * message box, due to lack of console. */
void pyi_debug_dialog_error(const char *fmt, ...);
void pyi_debug_dialog_warning(const char *fmt, ...);
void pyi_debug_dialog_perror(const char *funcname, const char *fmt, ...);
void pyi_debug_dialog_winerror(const char *funcname, const char *fmt, ...);

#define PYI_ERROR pyi_debug_dialog_error
#define PYI_WARNING pyi_debug_dialog_warning
#define PYI_PERROR pyi_debug_dialog_perror
#define PYI_WINERROR pyi_debug_dialog_winerror

#else /* defined(_WIN32) && defined(WINDOWED) */

/* POSIX and Windows console mode; display error messages to stderr. */
void pyi_debug_printf(const char *fmt, ...);
void pyi_debug_perror(const char *funcname, const char *fmt, ...);

#define PYI_ERROR pyi_debug_printf
#define PYI_WARNING pyi_debug_printf
#define PYI_PERROR pyi_debug_perror

#ifdef _WIN32
void pyi_debug_winerror(const char *funcname, const char *fmt, ...);
#define PYI_WINERROR pyi_debug_winerror
#endif /* ifdef _WIN32 */

#endif /* defined(_WIN32) && defined(WINDOWED) */

/* Debug messages */
#ifdef LAUNCH_DEBUG

#if defined(_WIN32) && defined(WINDOWED)
    /* We do not have console; emit messages via OutputDebugString
     * win32 API */
    void pyi_debug_win32debug(const char *fmt, ...);
    #define PYI_DEBUG pyi_debug_win32debug
#else
    /* We have console; emit messages to stderr */
    #define PYI_DEBUG pyi_debug_printf
#endif /* defined(_WIN32) && defined(WINDOWED) */

#else /* ifdef LAUNCH_DEBUG */

/* MSVC does not allow empty vararg macro... */
#if defined(_WIN32) && defined(_MSC_VER)
    #define PYI_DEBUG
#else
    #define PYI_DEBUG(...)
#endif /* defined(_WIN32) && defined(_MSC_VER) */

#endif /* ifdef LAUNCH_DEBUG */


/*
 * Path and string macros.
 */
#ifdef _WIN32
    #define PYI_PATHSEP    ';'
    #define PYI_CURDIR     '.'
    #define PYI_SEP        '\\'
    /* For some functions like strcat() we need to pass
     * string and not only char. */
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

/* File seek and tell with large (64-bit) offsets */
#if defined(_WIN32) && defined(_MSC_VER)
    #define pyi_fseek _fseeki64
    #define pyi_ftell _ftelli64
#else
    #define pyi_fseek fseeko
    #define pyi_ftell ftello
#endif

/* MSVC provides _stricmp() in-lieu of POSIX strcasecmp() */
#if defined(_WIN32) && defined(_MSC_VER)
    #define strcasecmp(string1, string2) _stricmp(string1, string2)
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

#endif /* PYI_GLOBAL_H */
