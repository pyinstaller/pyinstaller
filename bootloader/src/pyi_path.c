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
 * Path manipulation utilities.
 */

/* TODO: use safe string functions */
#define _CRT_SECURE_NO_WARNINGS 1

#include <sys/types.h> /* struct stat, struct _stat */
#include <sys/stat.h>  /* stat() */

#ifdef _WIN32
    #include <windows.h>  /* GetModuleFileNameW */
    #include <wchar.h>
#elif __APPLE__
    #include <libgen.h>      /* basename(), dirname() */
    #include <mach-o/dyld.h> /* _NSGetExecutablePath() */
#else
    #include <libgen.h>  /* basename() */
    #include <limits.h>  /* PATH_MAX */
    #include <unistd.h>  /* unlink */
#endif

#include <stdio.h>  /* FILE, fopen */
#include <stdlib.h> /* _fullpath, realpath */
#include <string.h>

/* PyInstaller headers. */
#include "pyi_global.h"  /* PATH_MAX */
#include "pyi_utils.h"
#include "pyi_win32_utils.h"
#include "pyi_python27_compat.h"  /* is_py2 */

/*
 * Giving a fullpath, it will copy to the buffer a string
 * which contains the path without last component.
 */
void
pyi_path_dirname(char *result, const char *path)
{
/* FIXME: This should be somthink like HAVE_DIRNAME */
#ifdef _WIN32
    size_t len = 0;
    char *match = NULL;

    /* Copy path to result and then just write '\0' to the place with path separator. */
    strncpy(result, path, strlen(path) + 1);
    /* Remove separator from the end. */
    len = strlen(result);

    if (result[len] == PYI_SEP) {
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
#else /* ifdef _WIN32 */
      /* Use dirname() for other platforms. */
    char *dirpart = NULL;
    char tmp[PATH_MAX];
    /* Copy path to 'tmp' because dirname() modifies the original string! */
    strcpy(tmp, path);

    dirpart = (char *) dirname((char *) tmp);  /* _XOPEN_SOURCE - no 'const'. */
    strcpy(result, dirpart);
#endif /* ifdef _WIN32 */
}

/*
 * Returns the last component of the path in filename. Return result
 * in new buffer.
 */
void
pyi_path_basename(char *result, const char *path)
{
/* FIXME: This should be somthink like HAVE_BASENAME */
#ifdef _WIN32
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
#endif /* ifdef _WIN32 */
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
    size_t len = 0;

    if (NULL == result) {
        len = strlen(path1) + strlen(path2) + 2;
        result = malloc(len);

        if (NULL == result) {
            return NULL;
        }

        memset(result, 0, len);
    }
    else {
        memset(result, 0, PATH_MAX);
    }
    /* Copy path1 to result without null terminator */
    strncpy(result, path1, strlen(path1));
    /* Append trailing slash if missing. */
    len = strlen(result);

    if (result[len - 1] != PYI_SEP) {
        result[len] = PYI_SEP;
        result[len + 1] = PYI_NULLCHAR;
    }
    /* Remove trailing slash from path2 if present. */
    len = strlen(path2);

    if (path2[len - 1] == PYI_SEP) {
        /* Append path2 without slash. */
        strncat(result, path2, len - 2);
    }
    else {
        /* path2 does not end with slash. */
        strcat(result, path2);
    }
    return result;
}

/* Normalize a pathname. Return result in new buffer. */
/* TODO implement this function */
void
pyi_path_normalize(char *result, const char *path)
{
}

/*
 * Return full path to a file. Wraps platform specific function.
 */
int
pyi_path_fullpath(char *abs, size_t abs_size, const char *rel)
{
#ifdef _WIN32
    /* TODO use _wfullpath - wchar_t function. */
    return _fullpath(abs, rel, abs_size) != NULL;
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
int
pyi_search_path(char * result, const char * appname)
{
    char * path = pyi_getenv("PATH");
    char dirname[PATH_MAX + 1];
    char filename[PATH_MAX + 1];

    if (NULL == path) {
        return -1;
    }

    while (1) {
        char *delim = strchr(path, PYI_PATHSEP);

        if (delim) {
            size_t len = delim - path;

            if (len > PATH_MAX) {
                len = PATH_MAX;
            }
            strncpy(dirname, path, len);
            *(dirname + len) = '\0';
        }
        else {  /* last $PATH element */
            strncpy(dirname, path, PATH_MAX);
        }
        pyi_path_join(filename, dirname, appname);

        if (pyi_path_exists(filename)) {
            strncpy(result, filename, PATH_MAX);
            return 0;
        }

        if (!delim) {
            break;
        }
        path = delim + 1;
    }
    return -1;
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
int
pyi_path_executable(char *execfile, const char *appname)
{
    char buffer[PATH_MAX];
    size_t result = -1;

#ifdef _WIN32
    wchar_t modulename_w[PATH_MAX];

    /* GetModuleFileNameW returns an absolute, fully qualified path
     */
    if (!GetModuleFileNameW(NULL, modulename_w, PATH_MAX)) {
        FATAL_WINERROR("GetModuleFileNameW", "Failed to get executable path.");
        return -1;
    }

    if (!pyi_win32_utils_to_utf8(execfile, modulename_w, PATH_MAX)) {
        FATALERROR("Failed to convert executable path to UTF-8.");
        return -1;
    }

#elif __APPLE__
    uint32_t length = sizeof(buffer);

    /* Mac OS X has special function to obtain path to executable.
     * This may return a symlink.
     */
    if (_NSGetExecutablePath(buffer, &length) != 0) {
        FATALERROR("System error - unable to load!\n");
        return -1;
    }

    if (pyi_path_fullpath(execfile, PATH_MAX, buffer) == false) {
        VS("LOADER: Cannot get fullpath for %s\n", execfile);
        return -1;
    }

#else /* ifdef _WIN32 */
    result = -1;
    /* On Linux, FreeBSD, and Solaris, we try these /proc paths first
     */
    #if defined(__linux__)
    result = readlink("/proc/self/exe", execfile, PATH_MAX);  /* Linux */
    #elif defined(__FreeBSD__)
    result = readlink("/proc/curproc/file", execfile, PATH_MAX);  /* FreeBSD */
    #elif defined(__sun)
    result = readlink("/proc/self/path/a.out", execfile, PATH_MAX);  /* Solaris */
    #endif

    if (-1 != result) {
        /* execfile is not yet zero-terminated. result is the byte count. */
        *(execfile + result) = '\0';
    }
    else {
        /* No /proc path found or provided
         */
        if (appname[0] == PYI_SEP || strchr(appname, PYI_SEP)) {
            /* Absolute or relative path.
             * Convert to absolute and resolve symlinks.
             */
            if (pyi_path_fullpath(execfile, PATH_MAX, appname) == false) {
                VS("LOADER: Cannot get fullpath for %s\n", execfile);
                return -1;
            }
        }
        else {
            /* Not absolute or relative path, just program name. Search $PATH
             */
            result = pyi_search_path(buffer, appname);

            if (-1 == result) {
                /* Searching $PATH failed, user is crazy. */
                VS("LOADER: Searching $PATH failed for %s", appname);
                strncpy(buffer, appname, PATH_MAX);
                if (buffer[PATH_MAX-1] != '\0') {
                    VS("LOADER: Appname too large %s\n", appname);
                    return -1;
                }
            }

            if (pyi_path_fullpath(execfile, PATH_MAX, buffer) == false) {
                VS("LOADER: Cannot get fullpath for %s\n", execfile);
                return -1;
            }
        }
    }
#endif /* ifdef _WIN32 */
    VS("LOADER: executable is %s\n", execfile);
    return 0;
}

/*
 * Return absolute path to homepath. It is the directory containing executable.
 */
void
pyi_path_homepath(char *homepath, const char *thisfile)
{
    /* Fill in here (directory of thisfile). */
    pyi_path_dirname(homepath, thisfile);
    VS("LOADER: homepath is %s\n", homepath);
}

/*
 * Return full path to an external PYZ-archive.
 * The name is based on the excutable's name: path/myappname.pkg
 *
 * archivefile - buffer where to put path the .pkg.
 * thisfile    - usually the executable's filename.
 */
void
pyi_path_archivefile(char *archivefile, const char *thisfile)
{
    strcpy(archivefile, thisfile);
#ifdef _WIN32
    strcpy(archivefile + strlen(archivefile) - 3, "pkg");
#else
    strcat(archivefile, ".pkg");
#endif
}

/*
 * Multiplatform wrapper around function fopen().
 */
#ifdef _WIN32
FILE*
pyi_path_fopen(const char* filename, const char* mode)
{
    wchar_t wfilename[MAX_PATH];
    wchar_t wmode[10];

    pyi_win32_utils_from_utf8(wfilename, filename, MAX_PATH);
    pyi_win32_utils_from_utf8(wmode, mode, 10);
    return _wfopen(wfilename, wmode);
}
#else
    #define pyi_path_fopen(x, y)    fopen(x, y)
#endif
