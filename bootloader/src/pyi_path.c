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
 * Path manipulation utilities.
 */

#include <sys/types.h> /* struct stat, struct _stat */
#include <sys/stat.h>  /* stat() */

#ifdef _WIN32
    #include <windows.h>
    #include <wchar.h>
    #ifdef __GNUC__
        #include <libgen.h> /* basename(), dirname() */
    #endif /* __GNUC__ */
#else /* _WIN32 */
    #include <libgen.h>  /* basename(), dirnmae() */
    #include <unistd.h>  /* unlink(), symlink() */
#endif /* _WIN32 */

#include <stdio.h>  /* FILE, fopen */
#include <stdlib.h> /* _fullpath, realpath */
#include <string.h>

/* PyInstaller headers. */
#include "pyi_path.h"
#include "pyi_global.h"  /* PYI_PATH_MAX */
#include "pyi_utils.h"

/*
 * Giving a fullpath, it will copy to the buffer a string
 * which contains the path without last component.
 */
bool
pyi_path_dirname(char *result, const char *path)
{
#ifndef HAVE_DIRNAME
    size_t len = 0;
    char *match = NULL;

    /* Copy path to result and then just write '\0' to the place with path separator. */
    if (snprintf(result, PYI_PATH_MAX, "%s", path) >= PYI_PATH_MAX) {
        return false;
    }

    /* Remove separator from the end. */
    len = strlen(result)-1;
    if (len >= 0 && result[len] == PYI_SEP) {
        result[len] = 0;
    }

    /* Remove the rest of the string. */
    match = strrchr(result, PYI_SEP);
    if (match != NULL) {
        *match = 0;
    }
    else {
        /* No dir separator found, so no dir-part, so use current dir */
        *result = PYI_CURDIR;
        result[1] = 0;
    }
#else /* ifndef HAVE_DIRNAME */
      /* Use dirname() for other platforms. */
    char *dirpart = NULL;
    char tmp[PYI_PATH_MAX];
    /* Copy path to 'tmp' because dirname() modifies the original string! */
    if (snprintf(tmp, PYI_PATH_MAX, "%s", path) >= PYI_PATH_MAX) {
        return false;
    }
    dirpart = (char *) dirname((char *) tmp);  /* _XOPEN_SOURCE - no 'const'. */
    if (snprintf(result, PYI_PATH_MAX, "%s", dirpart) >= PYI_PATH_MAX) {
        return false;
    }
#endif /* ifndef HAVE_DIRNAME */
    return true;
}

/*
 * Returns the last component of the path in filename. Return result
 * in new buffer.
 */
bool
pyi_path_basename(char *result, const char *path)
{
#ifndef HAVE_BASENAME
    /* Search for the last directory separator in PATH.  */
    char *basename = strrchr (path, '\\');

    if (!basename) {
        basename = strrchr (path, '/');
    }

    /* If found, return the address of the following character,
     *  or the start of the parameter passed in.  */
    strcpy(result, basename ? ++basename : (char*)path);
#else
    char *base = NULL;
    base = (char *) basename((char *) path);  /* _XOPEN_SOURCE - no 'const'. */
    strcpy(result, base);
#endif /* ifndef HAVE_BASENAME */
    return true;
}

/*
 * Join two path components.
 * Joined path is returned without slash at the end.
 *
 * If result is NULL, allocates and returns a new buffer which the caller
 * is responsible for freeing. Otherwise, result should be a buffer of at
 * least PYI_PATH_MAX characters.
 *
 * Returns NULL on failure.
 */
/* FIXME: Need to test for absolute path2 -- or mark this function as */
/*        only for an relative path2 */
char *
pyi_path_join(char *result, const char *path1, const char *path2)
{
    size_t len, len2;
    /* Copy path1 to result */
    len = snprintf(result, PYI_PATH_MAX, "%s", path1);
    if (len >= PYI_PATH_MAX-1) {
        return NULL;
    }
    /* Append trailing slash if missing. */
    if (result[len-1] != PYI_SEP) {
        result[len++] = PYI_SEP;
        result[len++] = 0;
    }
    len = PYI_PATH_MAX - len;
    len2 = strlen(path2);
    if (len2 >= len) {
        return NULL;
    };
    /* Remove trailing slash from path2 if present. */
    if (path2[len2 - 1] == PYI_SEP) {
        /* Append path2 without slash. */
        strncat(result, path2, len);
        result[strlen(result) - 1] = 0;
    }
    else {
        /* path2 does not end with slash. */
        strncat(result, path2, len);
    }
    return result;
}

int
pyi_path_exists(char * path)
{
#ifdef _WIN32
    wchar_t wpath[PYI_PATH_MAX + 1];
    struct _stat result;
    pyi_win32_utf8_to_wcs(path, wpath, PYI_PATH_MAX);
    return _wstat(wpath, &result) == 0;
#else
    struct stat result;
    return stat(path, &result) == 0;
#endif
}

/*
 * Multiplatform wrapper around function fopen().
 */
#ifdef _WIN32
FILE*
pyi_path_fopen(const char* filename, const char* mode)
{
    wchar_t wfilename[PYI_PATH_MAX];
    wchar_t wmode[10];

    pyi_win32_utf8_to_wcs(filename, wfilename, PYI_PATH_MAX);
    pyi_win32_utf8_to_wcs(mode, wmode, 10);
    return _wfopen(wfilename, wmode);
}
#endif

bool
pyi_path_is_symlink(const char *path)
{
#ifdef _WIN32
    wchar_t wpath[PYI_PATH_MAX + 1];
    pyi_win32_utf8_to_wcs(path, wpath, PYI_PATH_MAX);
    return pyi_win32_is_symlink(wpath);
#else
    struct stat buf;
    if (lstat(path, &buf) < 0) {
        return false;
    }
    return S_ISLNK(buf.st_mode);
#endif
}

/*
 * Create symbolic link.
 */
int
pyi_path_mksymlink(const char *link_target, const char *link_name)
{
#ifdef _WIN32
    static int unprivileged_create_available = 1;
    wchar_t wlink_target[PYI_PATH_MAX];
    wchar_t wlink_name[PYI_PATH_MAX];
    DWORD flags = 0;

    if (!pyi_win32_utf8_to_wcs(link_target, wlink_target, PYI_PATH_MAX)) {
        return -1;
    }
    if (!pyi_win32_utf8_to_wcs(link_name, wlink_name, PYI_PATH_MAX)) {
        return -1;
    }
    /* Creation of symbolic links in unprivileged mode was introduced
     * in Windows 10 build 14972. However, its requirement for Developer
     * Mode to be enabled makes it impractical for general cases. So
     * we implement full support here, but avoid creating symbolic links
     * on Windows in the first place...
     */
    if (unprivileged_create_available) {
        flags |= SYMBOLIC_LINK_FLAG_ALLOW_UNPRIVILEGED_CREATE;
    }
    if (CreateSymbolicLinkW(wlink_name, wlink_target, flags) == 0) {
        /* Check if the error was caused by use of SYMBOLIC_LINK_FLAG_ALLOW_UNPRIVILEGED_CREATE */
        if (unprivileged_create_available && GetLastError() == ERROR_INVALID_PARAMETER) {
            /* Disable it and try again */
            unprivileged_create_available = 0;
            return pyi_path_mksymlink(link_target, link_name);
        }
        return -1;
    }
    return 0;
#else
    return symlink(link_target, link_name);
#endif
}
