#ifndef HEADER_PYI_UTILS_H
#define HEADER_PYI_UTILS_H
/*
 * Portable wrapper for some utility functions like getenv/setenv
 * and file path manipulation.
 *
 * Copyright (C) 2012, Martin Zibricky
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

#include <limits.h>
#include <stdlib.h>

#ifdef WIN32
#include <windows.h>
#endif


/* Definition of type boolean. */
typedef int bool;
#define false 0
#define true  1


/* On Windows PATH_MAX does not exist but MAX_PATH does.
 * WinAPI MAX_PATH limit is only 256. MSVCR fuctions does not have this limit.
 * Redefine PATH_MAX for Windows to support longer path names.
 */
// TODO use MSVCR function for file path handling.
#ifdef WIN32
#define PATH_MAX 4096  /* Default value on Linux. */
#endif


/* Return string copy of environment variable. */
// TODO unicode support
static char *pyi_getenv(const char *variable)
{
    char *env = NULL;

#ifdef WIN32
    char  buf1[PATH_MAX], buf2[PATH_MAX];
    DWORD rc;

    rc = GetEnvironmentVariableA(variable, buf1, sizeof(buf1));
    if(rc > 0) {
        env = buf1;
        /* Expand environment variables like %VAR% in value. */
        rc = ExpandEnvironmentStringsA(env, buf2, sizeof(buf2));
        if(rc > 0) {
            env = buf1;
        }
    }
#else
    /* Standard POSIX function. */
    env = getenv(variable);
#endif
    /* Return copy of string. */
    return (env && env[0]) ? strdup(env) : NULL;
}


/* Set environment variable. */
// TODO unicode support
static int pyi_setenv(const char *variable, const char *value)
{
    int rc;
#ifdef WIN32
    rc = SetEnvironmentVariableA(variable, value);
#else
    rc = setenv(variable, value, true);
#endif
    return rc;
}


/* Unset environment variable. */
// TODO unicode support
static int pyi_unsetenv(const char *variable)
{
    int rc;
#ifdef WIN32
    rc = SetEnvironmentVariableA(variable, NULL);
#else
    rc = unsetenv(variable);
#endif
    return rc;
}


#endif /* HEADER_PY_UTILS_H */
