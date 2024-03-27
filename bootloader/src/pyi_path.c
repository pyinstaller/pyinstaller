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
    #include <windows.h>  /* GetModuleFileNameW */
    #include <wchar.h>
    #ifdef __GNUC__
        #include <libgen.h> /* basename(), dirname() */
    #endif
#elif __APPLE__
    #include <libgen.h>      /* basename(), dirname() */
    #include <mach-o/dyld.h> /* _NSGetExecutablePath() */
    #include <unistd.h>  /* symlink() */
#else
    #include <libgen.h>  /* basename() */
    #include <unistd.h>  /* unlink(), symlink() */
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
/* FIXME: Need to test for absolute path2 -- or mark this function as */
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
        result[len++] = 0;
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
        result[strlen(result) - 1] = 0;
    }
    else {
        /* path2 does not end with slash. */
        strncat(result, path2, len);
    }
    return result;
}

/*
 * Fully resolve the given path; canonicalize it and resolve symbolic
 * links. It is implicitly assumed that the output buffer is large
 * enough to accept up to PATH_MAX characters (including the terminating
 * NULL character).
 */
int
pyi_path_resolve(const char *path, char *resolved_path)
{
#ifdef _WIN32
    wchar_t wpath[PATH_MAX + 1];
    wchar_t wresolved_path[PATH_MAX + 1];

    HANDLE handle;
    DWORD ret;

    int offset = 0;

    pyi_win32_utils_from_utf8(wpath, path, PATH_MAX);

    /* Open file/directory handle */
    handle = CreateFileW(
        wpath, /* lpFileName */
        0, /* dwDesiredAccess */
        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, /* dwShareMode */
        NULL, /* lpSecurityAttributes */
        OPEN_EXISTING, /* dwCreationDisposition */
        FILE_ATTRIBUTE_NORMAL, /* dwFlagsAndAttributes*/
        NULL /* hTemplateFile */
    );
    if (handle == INVALID_HANDLE_VALUE) {
        return 0;
    }

    /* Fully resolve the path */
    ret = GetFinalPathNameByHandleW(
        handle,  /* hFile */
        wresolved_path, /* lpszFilePath */
        PATH_MAX, /* cchFilePath */
        FILE_NAME_NORMALIZED /* dwFlags */
    );

    CloseHandle(handle);

    if (ret == 0 || ret >= PATH_MAX) {
        /* Failure or insufficient buffer size */
        return  0;
    }

    /* Remove the extended path indicator, to avoid potential issues due
     * to its appearance in `sys.executable`, `sys._MEIPASS`, etc. */
    if (ret >= 4 && wcsncmp(L"\\\\?\\", wresolved_path, 4) == 0) {
        offset = 4;
    }

    return pyi_win32_utils_to_utf8(resolved_path, wresolved_path + offset, PATH_MAX) != NULL;
#else
    return realpath(path, resolved_path) != NULL;
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


#if defined(__linux__)

/*
 * Return 0 if the given executable name is in fact the ld.so dynamic loader.
 */
static bool
pyi_is_ld_linux_so(const char *execfile)
{
    char basename[PATH_MAX];
    int status;
    char loader_name[65] = "";
    int soversion = 0;

    pyi_path_basename(basename, execfile);

    /* Match the string against ld-*.so.X. In sscanf, the %s is greedy, so
     * instead we match with character group that disallows dot (.). Also
     * limit the name length; note that the output array must be one byte
     * larger, to include the terminating NULL character. */
    status = sscanf(basename, "ld-%64[^.].so.%d", loader_name, &soversion);
    if (status != 2) {
        return false;
    }

    /* If necessary, we could further validate the loader name and soversion
     * against known patterns:
     *  - ld-linux.so.2 (glibc, x86)
     *  - ld-linux-x86-64.so.2 (glibc, x86_64)
     *  - ld-linux-x32.so.2 (glibc, x32)
     *  - ld-linux-aarch64.so.1 (glibc, aarch64)
     *  - ld-musl-x86_64.so.1 (musl, x86_64)
     *  - ...
     */

    return true;
}

#endif /* defined(__linux__) */


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
    char program_path[PATH_MAX];
    uint32_t length = sizeof(program_path);

    /* Mac OS X has special function to obtain path to executable.
     * This may return a symlink.
     */
    if (_NSGetExecutablePath(program_path, &length) != 0) {
        FATALERROR("Failed to obtain executable path via _NSGetExecutablePath!\n");
        return false;
    }

    if (pyi_path_resolve(program_path, execfile) == false) {
        VS("LOADER: failed to resolve full path for %s\n", program_path);
        return false;
    }

#else /* ifdef _WIN32 */
    /* On Linux, Cygwin, FreeBSD, and Solaris, we try these /proc paths first
     */
    ssize_t name_len = -1;

    #if defined(__linux__) || defined(__CYGWIN__)
    name_len = readlink("/proc/self/exe", execfile, PATH_MAX-1);  /* Linux, Cygwin */
    #elif defined(__FreeBSD__)
    name_len = readlink("/proc/curproc/file", execfile, PATH_MAX-1);  /* FreeBSD */
    #elif defined(__sun)
    name_len = readlink("/proc/self/path/a.out", execfile, PATH_MAX-1);  /* Solaris */
    #endif

    if (name_len != -1) {
        /* execfile is not yet zero-terminated. result is the byte count. */
        execfile[name_len] = '\0';
    }

    /* On linux, we might have been launched using custom ld.so dynamic loader.
     * In that case, /proc/self/exe points to the ld.so executable, and we need
     * to ignore it. */
#if defined(__linux__)
    if (pyi_is_ld_linux_so(execfile) == true) {
        VS("LOADER: resolved executable name %s is ld.so dynamic loader - ignoring it!\n", execfile);
        name_len = -1;
    }
#endif

    if (name_len == -1) {
        /* We failed to resolve the executable file via /proc (or we were
         * launched via ld.so dynamic loader). Try to manually resolve the
         * program path/name given via argv[0]. */
        if (strchr(appname, PYI_SEP)) {
            /* Absolute or relative path was given. Canonicalize it, and
             * resolve symbolic links. */
            VS("LOADER: resolving program path %s...\n", appname);
            if (pyi_path_resolve(appname, execfile) == false) {
                VS("LOADER: failed to resolve full path for %s\n", appname);
                return false;
            }
        } else {
            /* No path, just program name. Search $PATH for executable
             * with matching name. */
            char program_path[PATH_MAX];
            if (pyi_search_path(program_path, appname)) {
                /* Program found in $PATH; resolve full path */
                VS("LOADER: program %s found in PATH: %s. Resolving full path...\n", appname, program_path);
                if (pyi_path_resolve(program_path, execfile) == false) {
                    VS("LOADER: failed to resolve full path for %s\n", program_path);
                    return false;
                }
            } else {
                /* Searching $PATH failed; try resolving the name as-is,
                 * and hope for the best. NOTE: can we even reach this
                 * part? How was the executable even launched in such
                 * case? */
                VS("LOADER: could not find %s in $PATH! Attempting to resolve as-is...\n", appname);
                if (pyi_path_resolve(appname, execfile) == false) {
                    VS("LOADER: failed to resolve full path for %s\n", appname);
                    return false;
                }
            }
        }
    }

#endif /* ifdef _WIN32 */

    /* Check if execfile is a symbolic link. The macOS and POSIX codepaths should
     * already take care of resolving symbolic links, while Windows codepath does
     * not. Keep this as a common step nevertheless, just in case. */
    if (pyi_path_is_symlink(execfile)) {
        char orig_execfile[PATH_MAX];

        VS("LOADER: executable %s is a symbolic link - resolving...\n", execfile);

        /* Create a copy of original name; we need this to resolve relative symbolic
         * link (as well as for the error message). */
        if (snprintf(orig_execfile, PATH_MAX, "%s", execfile) >= PATH_MAX) {
            return false;
        }

        /* Fully resolve the path */
        if (pyi_path_resolve(orig_execfile, execfile) == false) {
            VS("LOADER: failed to resolve executable symbolic link %s\n", orig_execfile);
            return false;
        }
    }

    VS("LOADER: executable is %s\n", execfile);
    return true;
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

bool
pyi_path_is_symlink(const char *path)
{
#ifdef _WIN32
    wchar_t wpath[PATH_MAX + 1];
    pyi_win32_utils_from_utf8(wpath, path, PATH_MAX);
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
 * Create directory.
 */
int
pyi_path_mkdir(const char *path)
{
#ifdef _WIN32
    wchar_t wpath[PATH_MAX];
    pyi_win32_utils_from_utf8(wpath, path, PATH_MAX);
    return pyi_win32_mkdir(wpath);
#else
    return mkdir(path, 0700);
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
    wchar_t wlink_target[PATH_MAX];
    wchar_t wlink_name[PATH_MAX];
    DWORD flags = 0;

    if (!pyi_win32_utils_from_utf8(wlink_target, link_target, PATH_MAX)) {
        return -1;
    }
    if (!pyi_win32_utils_from_utf8(wlink_name, link_name, PATH_MAX)) {
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
