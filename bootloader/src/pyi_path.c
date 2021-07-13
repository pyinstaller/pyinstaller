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
 * Path manipulation utilities.
 */

#include <sys/types.h> /* struct stat, struct _stat */
#include <sys/stat.h>  /* stat() */

#ifdef _WIN32
    #include <windows.h>  /* GetModuleFileNameW */
    #include <wchar.h>
    #ifdef __GNUC__
        #include <libgen.h> /* basename(), dirname() */
    #endif
#elif __APPLE__
    #include <libgen.h>      /* basename(), dirname() */
    #include <mach-o/dyld.h> /* _NSGetExecutablePath() */
#else
    #include <libgen.h>  /* basename() */
    #include <unistd.h>  /* unlink */
#endif

#include <stdio.h>  /* FILE, fopen */
#include <stdlib.h> /* _fullpath, realpath */
#include <string.h>

/* PyInstaller headers. */
#include "pyi_path.h"
#include "pyi_global.h"  /* PATH_MAX */
#include "pyi_utils.h"
#include "pyi_win32_utils.h"

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
    if (snprintf(result, PATH_MAX, "%s", path) >= PATH_MAX) {
        return false;
    }

    /* Remove separator from the end. */
    len = strlen(result)-1;
    if (len >= 0 && result[len] == PYI_SEP) {
        result[len] = PYI_NULLCHAR;
    }

    /* Remove the rest of the string. */
    match = strrchr(result, PYI_SEP);
    if (match != NULL) {
        *match = PYI_NULLCHAR;
    }
    else {
        /* No dir separator found, so no dir-part, so use current dir */
        *result = PYI_CURDIR;
        result[1] = PYI_NULLCHAR;
    }
#else /* ifndef HAVE_DIRNAME */
      /* Use dirname() for other platforms. */
    char *dirpart = NULL;
    char tmp[PATH_MAX];
    /* Copy path to 'tmp' because dirname() modifies the original string! */
    if (snprintf(tmp, PATH_MAX, "%s", path) >= PATH_MAX) {
        return false;
    }
    dirpart = (char *) dirname((char *) tmp);  /* _XOPEN_SOURCE - no 'const'. */
    if (snprintf(result, PATH_MAX, "%s", dirpart) >= PATH_MAX) {
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
 * least PATH_MAX characters.
 *
 * Returns NULL on failure.
 */
/* FIXME: Need to test for absolut path2 -- or mark this function as */
/*        only for an relative path2 */
char *
pyi_path_join(char *result, const char *path1, const char *path2)
{
    size_t len, len2;
    /* Copy path1 to result */
    len = snprintf(result, PATH_MAX, "%s", path1);
    if (len >= PATH_MAX-1) {
        return NULL;
    }
    /* Append trailing slash if missing. */
    if (result[len-1] != PYI_SEP) {
        result[len++] = PYI_SEP;
        result[len++] = PYI_NULLCHAR;
    }
    len = PATH_MAX - len;
    len2 = strlen(path2);
    if (len2 >= len) {
        return NULL;
    };
    /* Remove trailing slash from path2 if present. */
    if (path2[len2 - 1] == PYI_SEP) {
        /* Append path2 without slash. */
        strncat(result, path2, len);
        result[strlen(result) - 1] = PYI_NULLCHAR;
    }
    else {
        /* path2 does not end with slash. */
        strncat(result, path2, len);
    }
    return result;
}


#if !defined(_WIN32) && !defined(__APPLE__)
/*
 * Return full path to a file's directory, but keeps the basename.
 * This is required to pass the correct basename to execvp().
 */
int
pyi_path_fullpath_keep_basename(char *abs, const char *rel)
{
    char dirname[PATH_MAX];
    char full_dirname[PATH_MAX];
    char basename[PATH_MAX];
    pyi_path_basename(basename, rel);
    pyi_path_dirname(dirname, rel);
    if (realpath(dirname, full_dirname) == NULL) {
        return false;
    }
    return (pyi_path_join(abs, full_dirname, basename) != NULL);
}
#endif

/*
 * Return full path to a file. Wraps platform specific function.
 */
int
pyi_path_fullpath(char *abs, size_t abs_size, const char *rel)
{
#ifdef _WIN32
    wchar_t wrel[PATH_MAX + 1];
    wchar_t *wabs = NULL;

    pyi_win32_utils_from_utf8(wrel, rel, PATH_MAX);

    wabs = _wfullpath(NULL, wrel, PATH_MAX);
    if (wabs == NULL) {
        return 0;
    }

    char *ret = pyi_win32_utils_to_utf8(abs, wabs, abs_size);
    free(wabs);

    return ret != NULL;
#else
    return realpath(rel, abs) != NULL;
#endif
}

int
pyi_path_exists(char * path)
{
#ifdef _WIN32
    wchar_t wpath[PATH_MAX + 1];
    struct _stat result;
    pyi_win32_utils_from_utf8(wpath, path, PATH_MAX);
    return _wstat(wpath, &result) == 0;
#else
    struct stat result;
    return stat(path, &result) == 0;
#endif
}

/* Search $PATH for the program named 'appname' and return its full path.
 * 'result' should be a buffer of at least PATH_MAX characters.
 */
bool
pyi_search_path(char * result, const char * appname)
{
    char *path = pyi_getenv("PATH"); // returns a copy
    char *dirname;

    if (NULL == path) {
        return false;
    }

    dirname = strtok(path, PYI_PATHSEPSTR);
    while (dirname != NULL) {
        if ((pyi_path_join(result, dirname, appname) != NULL)
            && pyi_path_exists(result)) {
            return true;
        }
        dirname = strtok(NULL, PYI_PATHSEPSTR);
    }
    return false;
}

/*
 * Return full path to the current executable.
 * Executable is the .exe created by pyinstaller: path/myappname.exe
 * Because the calling process can set argv[0] to whatever it wants,
 * we use a few alternate methods to get the executable path.
 *
 * execfile - buffer where to put path to executable.
 * appname - usually the item argv[0].
 */
bool
pyi_path_executable(char *execfile, const char *appname)
{
#ifdef _WIN32
    wchar_t modulename_w[PATH_MAX];

    /* GetModuleFileNameW returns an absolute, fully qualified path
     */
    if (!GetModuleFileNameW(NULL, modulename_w, PATH_MAX)) {
        FATAL_WINERROR("GetModuleFileNameW", "Failed to get executable path.\n");
        return false;
    }

    if (!pyi_win32_utils_to_utf8(execfile, modulename_w, PATH_MAX)) {
        FATALERROR("Failed to convert executable path to UTF-8.\n");
        return false;
    }

#elif __APPLE__
    char buffer[PATH_MAX];
    uint32_t length = sizeof(buffer);

    /* Mac OS X has special function to obtain path to executable.
     * This may return a symlink.
     */
    if (_NSGetExecutablePath(buffer, &length) != 0) {
        FATALERROR("System error - unable to load!\n");
        return false;
    }

    if (pyi_path_fullpath(execfile, PATH_MAX, buffer) == false) {
        VS("LOADER: Cannot get fullpath for %s\n", execfile);
        return false;
    }

#else /* ifdef _WIN32 */
    /* On Linux, Cygwin, FreeBSD, and Solaris, we try these /proc paths first
     */
    size_t name_len = -1;

    #if defined(__linux__) || defined(__CYGWIN__)
    name_len = readlink("/proc/self/exe", execfile, PATH_MAX-1);  /* Linux, Cygwin */
    #elif defined(__FreeBSD__)
    name_len = readlink("/proc/curproc/file", execfile, PATH_MAX-1);  /* FreeBSD */
    #elif defined(__sun)
    name_len = readlink("/proc/self/path/a.out", execfile, PATH_MAX-1);  /* Solaris */
    #endif

    if (name_len != -1) {
        /* execfile is not yet zero-terminated. result is the byte count. */
        *(execfile + name_len) = '\0';
    } else {
        if (strchr(appname, PYI_SEP)) {
            /* Absolute or relative path: Canonicalize directory path,
             * but keep original basename.
             */
            if (pyi_path_fullpath_keep_basename(execfile, appname) == false) {
                VS("LOADER: Cannot get fullpath for %s\n", execfile);
                return false;
            }
        }
        else {
            /* No absolute or relative path, just program name: search $PATH.
             */
            char buffer[PATH_MAX];
            if (! pyi_search_path(buffer, appname)) {
                /* Searching $PATH failed, user is crazy. */
                VS("LOADER: Searching $PATH failed for %s\n", appname);
                if (snprintf(buffer, PATH_MAX, "%s", appname) >= PATH_MAX) {
                    VS("LOADER: Full path to application exceeds PATH_MAX: %s\n", appname);
                    return false;
                }
            }
            if (pyi_path_fullpath_keep_basename(execfile, buffer) == false) {
                VS("LOADER: Cannot get fullpath for %s\n", execfile);
                return false;
            }
        }
    }
#endif /* ifdef _WIN32 */
    VS("LOADER: executable is %s\n", execfile);
    return true;
}

/*
 * Return absolute path to homepath. It is the directory containing executable.
 */
bool
pyi_path_homepath(char *homepath, const char *thisfile)
{
    /* Fill in here (directory of thisfile). */
    bool rc = pyi_path_dirname(homepath, thisfile);
    VS("LOADER: homepath is %s\n", homepath);
    return rc;
}

/*
 * Return full path to an external PYZ-archive.
 * The name is based on the excutable's name: path/myappname.pkg
 *
 * archivefile - buffer where to put path the .pkg.
 * thisfile    - usually the executable's filename.
 */
bool
pyi_path_archivefile(char *archivefile, const char *thisfile)
{
#ifdef _WIN32
    strcpy(archivefile, thisfile);
    strcpy(archivefile + strlen(archivefile) - 3, "pkg");
    return true;
#else
    return (snprintf(archivefile, PATH_MAX, "%s.pkg", thisfile) < PATH_MAX);
#endif
}

/*
 * Multiplatform wrapper around function fopen().
 */
#ifdef _WIN32
FILE*
pyi_path_fopen(const char* filename, const char* mode)
{
    wchar_t wfilename[PATH_MAX];
    wchar_t wmode[10];

    pyi_win32_utils_from_utf8(wfilename, filename, PATH_MAX);
    pyi_win32_utils_from_utf8(wmode, mode, 10);
    return _wfopen(wfilename, wmode);
}
#endif
