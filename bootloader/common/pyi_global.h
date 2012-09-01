/*
 * Glogal shared declarations used in many bootloader files.
 *
 * Copyright (C) 2012, Martin Zibricky
 * Copyright (C) 2005, Giovanni Bajo
 * Based on previous work under copyright (c) 2002 McMillan Enterprises, Inc.
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; either version 2
 * of the License, or (at your option) any later version.
 *
 * In addition to the permissions in the GNU General Public License, the
 * authors give you unlimited permission to link or embed the compiled
 * version of this file into combinations with other programs, and to
 * distribute those combinations without any restriction coming from the
 * use of this file. (The General Public License restrictions do apply in
 * other respects; for example, they cover modification of the file, and
 * distribution when not linked into a combine executable.)
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA
 */
#ifndef HEADER_PYI_GLOBAL_H
#define HEADER_PYI_GLOBAL_H

/*
 * Definition of type boolean. On OSX boolean type is available.
 */
typedef int bool_t;

#define false 0
#define true  1


/* Type type for dynamic library. */
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
#else
    #include <limits.h>  /* PATH_MAX available in this header. */
#endif

/*
 * Debug and error macros.
 */

#if defined(WIN32) && defined(WINDOWED)
    #define FATALERROR mbfatalerror
    #define OTHERERROR mbothererror
#else
    #define FATALERROR printf
    #define OTHERERROR printf
#endif

#ifdef LAUNCH_DEBUG
# if defined(WIN32) && defined(WINDOWED)
#  define VS mbvs
# else
#  define VS printf
# endif
#else
# ifdef WIN32
#  define VS
# else
#  define VS(...)
# endif
#endif


#ifdef WIN32
    #define PATHSEP ";"
    #define SEP '\\'
#else
    #define PATHSEP ":"
    #define SEP '/'
#endif

#endif /* HEADER_PYI_GLOBAL_H */
