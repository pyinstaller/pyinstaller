#ifndef HEADER_PYI_UTILS_H
#define HEADER_PYI_UTILS_H
/*
 * Portable wrapper for some utility functions like getenv/setenv,
 * file path manipulation and other shared data types or functions.
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
#include <string.h>

#ifdef WIN32
#include <windows.h>
#endif

/*
 * Function 'mkdtemp' (make temporary directory) is missing on some *nix platforms: 
 * - On Solaris function 'mkdtemp' is missing.
 * - On AIX 5.2 function 'mkdtemp' is missing. It is there in version 6.1 but we don't know
 *   the runtime platform at compile time, so we always include our own implementation on AIX.
 */
#if defined(SUNOS) || defined(AIX)
#include "mkdtemp.h"
#endif


#include "launch.h"  /* ARCHIVE_STATUS struct */


/* Definition of type boolean. */
typedef int bool;
#define false 0
#define true  1


/*
 * On Windows PATH_MAX does not exist but MAX_PATH does.
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


#ifdef WIN32

// TODO rename fuction and revisit
int pyi_get_temp_path(char *buff)
{
    int i;
    char *ret;
    char prefix[16];

    GetTempPath(MAX_PATH, buff);
    sprintf(prefix, "_MEI%d", getpid());

    // Windows does not have a race-free function to create a temporary
    // directory. Thus, we rely on _tempnam, and simply try several times
    // to avoid stupid race conditions.
    for (i=0;i<5;i++) {
        // TODO use race-free fuction - if any exists?
        ret = _tempnam(buff, prefix);
        if (mkdir(ret) == 0) {
            strcpy(buff, ret);
            strcat(buff, "\\");
            free(ret);
            return 1;
        }
        free(ret);
    }
    return 0;
}

#else

// TODO merge this function with windows version.
int pyi_get_temp_path(char *buff)
{
    // TODO Do we need to check on unix for common variables paths to temp dirs?
	static const char *envname[] = {
		"TMPDIR", "TEMP", "TMP", 0
	};
	static const char *dirname[] = {
		"/tmp", "/var/tmp", "/usr/tmp", 0
	};
	int i;
	char *p;
	for ( i=0; envname[i]; i++ ) {
		p = pyi_getenv(envname[i]);
		if (p) {
			strcpy(buff, p);
			if (pyi_test_temp_path(buff))
				return 1;
		}
	}
	for ( i=0; dirname[i]; i++ ) {
		strcpy(buff, dirname[i]);
		if (pyi_test_temp_path(buff))
			return 1;
	}
    return 0;
}

// TODO Is this really necessary to test for temp path? Why not just use mkdtemp()?
int pyi_test_temp_path(char *buff)
{
	strcat(buff, "/_MEIXXXXXX");
    if (mkdtemp(buff))
    {
        strcat(buff, "/");
        return 1;
    }
    return 0;
}


#endif


/*
 * Creates a temporany directory if it doesn't exists
 * and properly sets the ARCHIVE_STATUS members.
 */
static int pyi_create_temp_path(ARCHIVE_STATUS *status)
{
#ifdef WIN32
	char *p;
#endif

	if (status->temppath[0] == '\0') {
		if (!pyi_get_temp_path(status->temppath))
		{
            FATALERROR("INTERNAL ERROR: cannot create temporary directory!\n");
            return -1;
		}
#ifdef WIN32
		strcpy(status->temppathraw, status->temppath);
		for ( p=status->temppath; *p; p++ )
			if (*p == '\\')
				*p = '/';
#endif
	}
    return 0;
}


#endif /* HEADER_PY_UTILS_H */
