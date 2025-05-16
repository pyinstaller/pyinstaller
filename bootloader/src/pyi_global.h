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


/* These macros are used to define prototypes for imported functions,
 * to define corresponding entries in the function-table structures,
 * and to populate those entries:
 *  - PYI_EXT_FUNC_PROTO: given function's return type, name, and arguments,
 *    creates a typedef prototype called _PYI_{name}_TYPE.
 *  - PYI_EXT_FUNC_ENTRY: given function's name, generates the entry
 *    for function-table structure, under assumption that prototype has
 *    already been defined using via PYI_EXT_FUNC_PROTO.
 *  - PYI_EXT_FUNC_BIND: given handle to loaded shared library, name
 *    of the symbol to bind, and pointer to destination location, attempts
 *    to bind the function (using GetProcAddress on Windows, dlsym on
 *    other platforms).. The destination location is typically a field in
 *    function-table structure, defined via PYI_EXT_FUNC_ENTRY.
 */
#ifdef _WIN32
    typedef HMODULE pyi_dylib_t;

    #define PYI_EXT_FUNC_PROTO(result, name, args) \
        typedef result (__cdecl *_PYI_ ## name ## _TYPE) args;

    #define PYI_EXT_FUNC_ENTRY(name) \
        _PYI_ ## name ##_TYPE name;

    /* GetProcAddress() returns FARPROC, a function pointer, which can
     * be cast to a different function pointer. */
    #define PYI_EXT_FUNC_BIND(handle, name, dest) \
        dest = (_PYI_ ## name ## _TYPE)GetProcAddress(handle, #name);

#else /* ifdef _WIN32 */
    #include <dlfcn.h> /* dlsym(), dlerror() */

    typedef void * pyi_dylib_t;

    #define PYI_EXT_FUNC_PROTO(result, name, args) \
        typedef result (*_PYI_ ## name ## _TYPE) args;

    #define PYI_EXT_FUNC_ENTRY(name) \
        _PYI_ ## name ##_TYPE name;

    /* dlsym() returns a void * pointer, which is an object pointer.
     * ISO C explicitly forbids casts from object to function pointers
     * (in theory, the two could have different storage type, although
     * in practice, the cast should be safe on contemporary platforms).
     * To avoid warnings when using gcc with -pedantic option turned on,
     * we perform type-punning through union. */
    #define PYI_EXT_FUNC_BIND(handle, name, dest) \
        do {\
            /* This union requires its own scope */ \
            union { \
                _PYI_ ## name ## _TYPE func_ptr; \
                void *obj_ptr; \
            } alias; \
            /* Store object pointer */ \
            alias.obj_ptr = dlsym(handle, #name); \
            /* Read function pointer */ \
            dest = alias.func_ptr; \
        } while(0)

#endif  /* ifdef _WIN32 */


/*
 * Debug and error macros:
 *  - PYI_DEBUG
 *  - PYI_WARNING
 *  - PYI_ERROR
 *  - PYI_PERROR
 *
 * On Windows, additional macros are available for native wide-char
 * strings:
 *  - PYI_DEBUG_W
 *  - PYI_WARNING_W
 *  - PYI_ERROR_W
 *  - PYI_PERROR_W
 *  - PYI_WINERROR_W
 */

#include <errno.h>  /* errno */

#if defined(_WIN32)
    /* On Windows, we have separate implementations of these functions
     * for console and for windowed/noconsole mode. */
    void pyi_error_message(const char *fmt, ...);
    void pyi_warning_message(const char *fmt, ...);
    void pyi_perror_message(const char *funcname, int error_code, const char *fmt, ...);

    void pyi_error_message_w(const wchar_t *fmt, ...);
    void pyi_warning_message_w(const wchar_t *fmt, ...);
    void pyi_perror_message_w(const wchar_t *funcname, int error_code, const wchar_t *fmt, ...);
    void pyi_winerror_message_w(const wchar_t *funcname, DWORD error_code, const wchar_t *fmt, ...);

    #define PYI_ERROR(...) pyi_error_message(__VA_ARGS__)
    #define PYI_WARNING(...) pyi_warning_message(__VA_ARGS__)
    #define PYI_PERROR(funcname, ...) pyi_perror_message(funcname, errno, __VA_ARGS__)

    #define PYI_ERROR_W(...) pyi_error_message_w(__VA_ARGS__)
    #define PYI_WARNING_W(...) pyi_warning_message_w(__VA_ARGS__)
    #define PYI_PERROR_W(funcname, ...) pyi_perror_message_w(funcname, errno, __VA_ARGS__)
    #define PYI_WINERROR_W(funcname, ...) pyi_winerror_message_w(funcname, GetLastError(), __VA_ARGS__)

    #if defined(LAUNCH_DEBUG)
        void pyi_debug_message(const char *fmt, ...);
        void pyi_debug_message_w(const wchar_t *fmt, ...);

        #define PYI_DEBUG(...) pyi_debug_message(__VA_ARGS__)
        #define PYI_DEBUG_W(...) pyi_debug_message_w(__VA_ARGS__)
    #else
        /* MSVC does not allow empty vararg macro; but clang + MSVC does */
        #if defined(_MSC_VER) && !defined(__clang__)
            #define PYI_DEBUG
            #define PYI_DEBUG_W
        #else
            #define PYI_DEBUG(...)
            #define PYI_DEBUG_W(...)
        #endif
    #endif /* defined(LAUNCH_DEBUG) */
#else /* defined(_WIN32) */
    /* POSIX; display error messages to stderr. */
    void pyi_error_message(const char *fmt, ...);
    void pyi_warning_message(const char *fmt, ...);
    void pyi_perror_message(const char *funcname, int error_code, const char *fmt, ...);

    #define PYI_ERROR(...) pyi_error_message(__VA_ARGS__)
    #define PYI_WARNING(...) pyi_warning_message(__VA_ARGS__)
    #define PYI_PERROR(funcname, ...) pyi_perror_message(funcname, errno, __VA_ARGS__)

    #if defined(LAUNCH_DEBUG)
        void pyi_debug_message(const char *fmt, ...);
        #define PYI_DEBUG(...) pyi_debug_message(__VA_ARGS__)
    #else
        #define PYI_DEBUG(...)
    #endif
#endif /* defined(_WIN32) */


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
