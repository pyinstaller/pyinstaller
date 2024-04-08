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
 * Portable wrapper for some utility functions like getenv/setenv,
 * file path manipulation and other shared data types or functions.
 */

#ifdef _WIN32
    #include <windows.h>
    #include <direct.h>  /* _rmdir */
    #include <io.h>      /* _finddata_t */
    #include <process.h> /* getpid */
    #include <signal.h>  /* signal */
#else
    #include <dirent.h>
/*
 * On AIX  RTLD_MEMBER  flag is only visible when _ALL_SOURCE flag is defined.
 *
 * There are quite a few issues with xlC compiler. GCC is much better,
 * Without flag _ALL_SOURCE gcc get stuck on the RTLD_MEMBER flax when
 * compiling the bootloader.
 * This fix was tested wigh gcc on AIX6.1.
 */
    #if defined(AIX) && !defined(_ALL_SOURCE)
        #define _ALL_SOURCE
        #include <dlfcn.h>
        #undef  _ALL_SOURCE
    #else
        #include <dlfcn.h>
    #endif
    #include <signal.h>  /* kill, */
    #include <sys/wait.h>
    #include <unistd.h>  /* rmdir, unlink, mkdtemp */
#endif /* ifdef _WIN32 */
#ifndef SIGCLD
#define SIGCLD SIGCHLD /* not defined on OS X */
#endif
#ifndef sighandler_t
typedef void (*sighandler_t)(int);
#endif
#include <errno.h>
#include <stddef.h> /* ptrdiff_t */
#include <stdio.h>  /* FILE */
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h> /* struct stat */
#include <wchar.h>    /* wchar_t */

/* PyInstaller headers. */
#include "pyi_global.h"
#include "pyi_path.h"
#include "pyi_archive.h"
#include "pyi_main.h"
#include "pyi_utils.h"
#include "pyi_win32_utils.h"
#include "pyi_apple_events.h"


/**********************************************************************\
 *                  Environment variable management                   *
\**********************************************************************/
#ifdef _WIN32

char *
pyi_getenv(const char *variable)
{
    wchar_t *variable_w;
    wchar_t value[PATH_MAX];
    wchar_t expanded_value[PATH_MAX];
    DWORD rc;

    /* Convert the variable name from UTF-8 to wide-char */
    variable_w = pyi_win32_utils_from_utf8(NULL, variable, 0);

    /* Retrieve environment variable */
    rc = GetEnvironmentVariableW(variable_w, value, PATH_MAX);
    if (rc >= PATH_MAX) {
        return NULL; /* Insufficient buffer size */
    }
    if (rc == 0) {
        return NULL; /* Variable unavailable */
    }

    /* Expand environment variables within the environment variable's
     * value */
    rc = ExpandEnvironmentStringsW(value, expanded_value, PATH_MAX);
    if (rc >= PATH_MAX) {
        return NULL; /* Insufficient buffer size */
    }
    if (rc == 0) {
        return NULL; /* Error during expansion */
    }

    /* Convert to UTF-8 and return */
    return pyi_win32_utils_to_utf8(NULL, expanded_value, 0);
}

int
pyi_setenv(const char *variable, const char *value)
{
    int rc;
    wchar_t *variable_w;
    wchar_t *value_w;

    /* Convert from UTF-8 to wide-char */
    variable_w = pyi_win32_utils_from_utf8(NULL, variable, 0);
    value_w = pyi_win32_utils_from_utf8(NULL, value, 0);

    /* `SetEnvironmentVariableW` updates only the value in the process
     * environment block, while _wputenv_s updates the value in the CRT
     * block AND calls `SetEnvironmentVariableW` to update the process
     * environment block.
     *
     * Therefore, in order for modification to be visible to other CRT
     * functions (for example, `_wtempnam`), we must use `_wputenv_s`. */
    rc = _wputenv_s(variable_w, value_w);

    free(variable_w);
    free(value_w);

    return rc;
}

int
pyi_unsetenv(const char *variable)
{
    int rc;
    wchar_t *variable_w;

    /* Convert from UTF-8 to wide-char */
    variable_w = pyi_win32_utils_from_utf8(NULL, variable, 0);

    /* See the comment in `pyi_setenv`. As per MSDN, "You can remove a
     * variable from the environment by specifying an empty string (that
     * is, "") for value_string. */
    rc = _wputenv_s(variable_w, L"");

    free(variable_w);

    return rc;
}

#else /* ifdef _WIN32 */

char *
pyi_getenv(const char *variable)
{
    char *value;

    /* Use standard POSIX getenv(). */
    value = getenv(variable);

    /* On some POSIX platforms, `unsetenv` is not available. In such
     * cases, we "undefine" environment variables by setting them to
     * empty strings. Therefore, treat empty environment variables as
     * being undefined. */
    return (value && value[0]) ? strdup(value) : NULL; /* Return a copy */
}

int
pyi_setenv(const char *variable, const char *value)
{
    /* Standard POSIX function. */
    return setenv(variable, value, 1 /* overwrite */);
}

int
pyi_unsetenv(const char *variable)
{
#if HAVE_UNSETENV
    return unsetenv(variable);
#else /* HAVE_UNSETENV */
    /* If `unsetenv` is unavailable, set the variable to an empty string. */
    return setenv(variable, "", 1 /* overwrite */);
#endif /* HAVE_UNSETENV */
}


#endif /* ifdef _WIN32 */


/**********************************************************************\
 *         Temporary application top-level directory (onefile)        *
\**********************************************************************/
#ifdef _WIN32

/* Resolve the temporary directory specified by user via runtime_tmpdir
 * option, and create corresponding directory tree. */
static wchar_t *
_pyi_create_runtime_tmpdir(const char *runtime_tmpdir)
{
    wchar_t *runtime_tmpdir_w;
    wchar_t runtime_tmpdir_expanded[PATH_MAX];
    wchar_t *runtime_tmpdir_abspath;
    wchar_t *cursor;
    wchar_t directory_tree_path[PATH_MAX];
    DWORD rc;

    /* Convert UTF-8 path to wide-char */
    runtime_tmpdir_w = pyi_win32_utils_from_utf8(NULL, runtime_tmpdir, 0);
    if (!runtime_tmpdir_w) {
        FATALERROR("LOADER: failed to convert runtime-tmpdir to a wide string.\n");
        return NULL;
    }

    /* Expand environment variables like %LOCALAPPDATA% */
    rc = ExpandEnvironmentStringsW(runtime_tmpdir_w, runtime_tmpdir_expanded, PATH_MAX);
    free(runtime_tmpdir_w);
    if (!rc) {
        FATALERROR("LOADER: failed to expand environment variables in the runtime-tmpdir.\n");
        return NULL;
    }

    /* Resolve absolute path */
    if (pyi_win32_is_drive_root(runtime_tmpdir_expanded)) {
        /* Disk drive (e.g., "c:"); do not attempt to call _wfullpath(), because it will return
         * the current directory of this drive. So return a verbatim copy instead. */
        runtime_tmpdir_abspath = _wcsdup(runtime_tmpdir_expanded);
    } else {
        runtime_tmpdir_abspath = _wfullpath(NULL, runtime_tmpdir_expanded, PATH_MAX);
    }
    if (!runtime_tmpdir_abspath) {
        FATALERROR("LOADER: failed to obtain the absolute path of the runtime-tmpdir.\n");
        return NULL;
    }

    VS("LOADER: absolute runtime-tmpdir is %ls\n", runtime_tmpdir_abspath);

    /* Recursively create the directory structure
     *
     * NOTE: we call CreateDirectoryW without security descriptor for
     * this part of directory tree, as it might be shared by application
     * instances ran by different users. Only the last component (the
     * actual _MEIXXXXXX directory), created by the caller, uses security
     * descriptor to restrict access to current user.
     *
     * NOTE2: we ignore errors returned by CreateDirectoryW; if we
     * actually fail to create (a part of) directory tree here, we will
     * catch the error in the caller when trying to create the final
     * temporary directory component  (the actual _MEIXXXXXX directory).
     *
     * NOTE3: zero-clear the `directory_tree_path`, because `wcsncpy`
     * does not perform zero termination after it copies the string! */
    memset(directory_tree_path, 0, sizeof(directory_tree_path));
    cursor = wcschr(runtime_tmpdir_abspath, L'\\');
    while(cursor != NULL) {
        wcsncpy(directory_tree_path, runtime_tmpdir_abspath, cursor - runtime_tmpdir_abspath + 1);
        CreateDirectoryW(directory_tree_path, NULL);
        cursor = wcschr(++cursor, L'\\');
    }

    /* Run once more on full path, to handle cases when path did not end
     * with separator. */
    CreateDirectoryW(runtime_tmpdir_abspath, NULL);

    return runtime_tmpdir_abspath;
}

int
pyi_create_temporary_application_directory(PYI_CONTEXT *pyi_ctx)
{
    char *original_tmp_value = NULL;
    wchar_t prefix[16];
    wchar_t tempdir_path[PATH_MAX];
    int ret = 0;
    int i;

    /* If user specified the temporary directory via runtime_tmpdir
     * option, resolve it, create it, and store the path to TMP
     * environment variable to have`GetTempPathW` use it. */
    if (pyi_ctx->runtime_tmpdir != NULL) {
        wchar_t *runtime_tmpdir_w;
        DWORD rc;

        /* Retrieve original value of TMP environment variable, so we
         * can restore it at the very end of this function. */
        original_tmp_value = pyi_getenv("TMP");

        /* Resolve and create directory specified via the runtime_tmpdir
         * option. */
        runtime_tmpdir_w = _pyi_create_runtime_tmpdir(pyi_ctx->runtime_tmpdir);
        if (runtime_tmpdir_w == NULL) {
            free(original_tmp_value);
            return -1;
        }

        /* Store the path in the TMP environment variable. */
        rc = _wputenv_s(L"TMP", runtime_tmpdir_w);
        free(runtime_tmpdir_w);
        if (rc) {
            FATALERROR("LOADER: failed to set the TMP environment variable.\n");
            free(original_tmp_value);
            return -1;
        }

        VS("LOADER: successfully resolved the specified runtime-tmpdir\n");
    }

    /* Retrieve temporary directory */
    GetTempPathW(PATH_MAX, tempdir_path);

    /* Create _MEI + PID prefix */
    swprintf(prefix, 16, L"_MEI%d", getpid());

    /* Windows does not have a race-free function to create a temporary
     * directory. Thus, we rely on _tempnam, and simply try several times
     * to avoid stupid race conditions. */
    for (i = 0; i < 5; i++) {
        wchar_t *application_home_dir_w = _wtempnam(tempdir_path, prefix);

        /* Try creating the directory. Use `pyi_win32_mkdir` with security
         * descriptor to limit access to current user. */
        ret = pyi_win32_mkdir(application_home_dir_w, pyi_ctx->security_descriptor);

        if (ret == 0) {
            /* Convert path to UTF-8 and store it in main context structure */
            if (pyi_win32_utils_to_utf8(pyi_ctx->application_home_dir, application_home_dir_w, PATH_MAX) == NULL) {
                FATALERROR("LOADER: length of teporary directory path exceeds maximum path length!\n");
                ret = -1;
            }
            free(application_home_dir_w);
            break;
        } else {
            free(application_home_dir_w);
        }
    }

    /* If we modified TMP environment variable due to runtime_tmpdir
     * option, restore the environment variable to its original state. */
    if (pyi_ctx->runtime_tmpdir != NULL) {
        if (original_tmp_value!= NULL) {
            pyi_setenv("TMP", original_tmp_value);
            free(original_tmp_value);
        } else {
            pyi_unsetenv("TMP");
        }
    }

    return ret;
}

#else /* ifdef _WIN32 */

/*
 * Function 'mkdtemp' (make temporary directory) is missing on some POSIX platforms:
 * - On Solaris function 'mkdtemp' is missing.
 * - On AIX 5.2 function 'mkdtemp' is missing. It is there in version 6.1 but we don't know
 *   the runtime platform at compile time, so we always include our own implementation on AIX.
 */
#if !defined(HAVE_MKDTEMP)

static char *
mkdtemp(char *template)
{
    if (!mktemp(template) ) {
        return NULL;
    }

    if (mkdir(template, 0700) ) {
        return NULL;
    }

    return template;
}

#endif /* !defined(HAVE_MKDTEMP) */

/* Append the _MEIXXXXXX string to the temporary directory path template,
 * and try creating the temporary directory. */
static int
_pyi_format_and_create_tmpdir(char *tmpdir_path)
{
    size_t path_len;
    unsigned char needs_separator;

    /* Compute length of the given temporary directory path - to ensure
     * that strcat operations below do not exceed buffer length. */
    path_len = strlen(tmpdir_path);

    /* Check whether the given path ends with separator or not. Typically,
     * it should not, but on macOS, the value from $TMPDIR does. */
    needs_separator = tmpdir_path[path_len - 1] != PYI_SEP;

    /* Add separator , _MEI, and six X characters required by mkdtemp */
    path_len += needs_separator + 4 + 6;
    if (path_len >= PATH_MAX) {
        return -1;
    }

    if (needs_separator) {
        strcat(tmpdir_path, PYI_SEPSTR);
    }
    strcat(tmpdir_path, "_MEIXXXXXX");

    /* Try creating the directory */
    if (mkdtemp(tmpdir_path) == NULL) {
        return -1;
    }

    return 0;
}

int
pyi_create_temporary_application_directory(PYI_CONTEXT *pyi_ctx)
{
    static const char *candidate_env_vars[] = {
        "TMPDIR",
        "TEMP",
        "TMP"
    };

    static const char *candidate_tmp_dirs[] = {
        "/tmp",
        "/var/tmp",
        "/usr/tmp"
    };

    int i;

    /* If specified, use runtime_tmpdir */
    if (pyi_ctx->runtime_tmpdir != NULL) {
        if (snprintf(pyi_ctx->application_home_dir, PATH_MAX, "%s", pyi_ctx->runtime_tmpdir) >= PATH_MAX) {
            return -1;
        }

        return _pyi_format_and_create_tmpdir(pyi_ctx->application_home_dir);
    }

    /* Check the standard environment variables */
    for (i = 0; i < sizeof(candidate_env_vars)/sizeof(candidate_env_vars[0]); i++) {
        char *env_var_value = pyi_getenv(candidate_env_vars[i]);
        int ret;

        if (env_var_value == NULL) {
            continue;
        }

        ret = snprintf(pyi_ctx->application_home_dir, PATH_MAX, "%s", env_var_value);
        free(env_var_value);

        if (ret >= PATH_MAX) {
            continue;
        }

        if (_pyi_format_and_create_tmpdir(pyi_ctx->application_home_dir) == 0) {
            return 0;
        }
    }

    /* Check the standard temporary directory paths */
    for (i = 0; i < sizeof(candidate_tmp_dirs)/sizeof(candidate_tmp_dirs[0]); i++) {
         snprintf(pyi_ctx->application_home_dir, PATH_MAX, "%s", candidate_tmp_dirs[i]);
         if (_pyi_format_and_create_tmpdir(pyi_ctx->application_home_dir) == 0) {
            return 0;
        }
    }

    return -1; /* No suitable location found */
}

#endif /* ifdef _WIN32 */


/**********************************************************************\
 *                  Recursive removal of a directory                  *
\**********************************************************************/
/* Used for removal of temporary application top-level directory in
 * onefile builds. */

#ifdef _WIN32

/* The actual implementation with wide-char path */
static int
_pyi_recursive_rmdir(const wchar_t *dir_path)
{
    int dir_path_length;
    int buffer_size;
    wchar_t entry_path[PATH_MAX];
    HANDLE handle;
    WIN32_FIND_DATAW entry_info;

    /* Copy the directory path, and append separator and a wildcard for
     * the `FindFirstFileW()` call. Store the length of the directory
     * path plus the separator; this allows us to re-use the same buffer
     * for constructing entries' full paths, by overwriting only the
     * part of the string that follows the path separator that we added. */
    dir_path_length = _snwprintf(entry_path, PATH_MAX, L"%s\\*", dir_path);
    if (dir_path_length >= PATH_MAX) {
        return -1;
    }
    dir_path_length--; /* Ignore the wildcard at the end */
    buffer_size = PATH_MAX - dir_path_length; /* Remaining buffer size */

    /* Start the search by looking for first entry */
    handle = FindFirstFileW(entry_path, &entry_info);
    if (handle == INVALID_HANDLE_VALUE) {
        return -1;
    }

    do {
        /* Skip . and .. */
        if (wcscmp(entry_info.cFileName, L".") == 0 || wcscmp(entry_info.cFileName, L"..") == 0) {
            continue;
        }

        /* Construct the full path, by overwriting the part of string
         * that starts after path directory and separator. */
        if (_snwprintf(entry_path + dir_path_length, buffer_size, L"%s", entry_info.cFileName) >= buffer_size) {
            continue;
        }

        /* Deteremine the type of entry, and remove it. Ignore errors
         * here - if we fail to  remove an entry here, we will also fail
         * to remove the top-level directory.*/
        if (entry_info.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
            /* Avoid recursing into symlinked directories */
            unsigned char is_symlink = 0;

            if (entry_info.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT) {
                if (entry_info.dwReserved0 == IO_REPARSE_TAG_SYMLINK) {
                    is_symlink = 1;
                }
            }

            if (is_symlink) {
                /* Remove only the symlink itself */
                RemoveDirectoryW(entry_path);
            } else {
                /* Recurse into directory */
                _pyi_recursive_rmdir(entry_path);
            }
        } else {
            /* Delete file (or symlink to a file) */
            DeleteFileW(entry_path);
        }
    } while (FindNextFileW(handle, &entry_info) != 0);

    FindClose(handle);

    /* Finally, remove the directory */
    return RemoveDirectoryW(dir_path) != 1 ? -1 : 0; /* false/true-> -1/0 */
}


/* For now, the caller is supplying narrow-char path in  UTF-8 encoding. */
int
pyi_recursive_rmdir(const char *dir_path)
{
    wchar_t dir_path_w[PATH_MAX];
    pyi_win32_utils_from_utf8(dir_path_w, dir_path, PATH_MAX);
    return _pyi_recursive_rmdir(dir_path_w);
}


#else /* ifdef _WIN32 */


int
pyi_recursive_rmdir(const char *dir_path)
{
    DIR *dir_handle;
    struct dirent *dir_entry;
    struct stat stat_buf;
    int dir_path_length;
    int buffer_size;
    char entry_path[PATH_MAX];

    /* Make a copy of directory path (and append a path separator), into
     * mutable buffer that we will use to construct entries' full paths.
     * Store the length of the directory path string; this allows us to
     * overwrite only the sub-component part of the string, without having
     * to copy the directory path each time. */
    dir_path_length = snprintf(entry_path, PATH_MAX, "%s%c", dir_path, PYI_SEP);
    if (dir_path_length >= PATH_MAX) {
        return -1;
    }
    buffer_size = PATH_MAX - dir_path_length; /* Remaining buffer size */

    /* Open the directory */
    dir_handle = opendir(dir_path);
    if (dir_handle == NULL) {
        return -1;
    }

    /* Iterate over directory contents */
    for (dir_entry = readdir(dir_handle); dir_entry != NULL; dir_entry = readdir(dir_handle))
    {
        /* Skip . and .. */
        if (strcmp(dir_entry->d_name, ".") == 0 || strcmp(dir_entry->d_name, "..") == 0) {
            continue;
        }

        /* Construct the full path, by overwriting the part of string
         * that starts after path directory and separator. */
        if (snprintf(entry_path + dir_path_length, buffer_size, "%s", dir_entry->d_name) >= buffer_size) {
            continue;
        }

        /* Deteremine the type of entry, and remove it. Use lstat()
         * instead of stat() in order to prevent recursion into symlinked
         * directories. Ignore errors here - if we fail to remove an entry
         * here, we will also fail to remove the top-level directory.*/
        if (lstat(entry_path, &stat_buf) == 0) {
            if (S_ISDIR(stat_buf.st_mode) ) {
                /* Recurse into sub-directory */
                pyi_recursive_rmdir(entry_path);
            } else {
                unlink(entry_path);
            }
        }
    }
    closedir(dir_handle);

    /* Finally, remove the directory; the return value of rmdir (0 on
     * success, -1 on error) maps directly to this function's return. */
    return rmdir(dir_path);
}


#endif /* ifdef _WIN32 */


/**********************************************************************\
 *                    Misc. file/directory helpers                    *
\**********************************************************************/
/*
 * Helper that creates parent directory tree for the given filename,
 * rooted under the given prefix path. The prefix path is assumed to
 * already exist.
 *
 * Returns 0 on success, -1 on failure.
 */
int
pyi_create_parent_directory_tree(const PYI_CONTEXT *pyi_ctx, const char *prefix_path, const char *filename)
{
    char filename_copy[PATH_MAX];
    char path[PATH_MAX];
    char *dir_component;
    size_t path_length;

    /* We need to make a copy of filename for strtok() */
    snprintf(filename_copy, PATH_MAX, "%s", filename);

    /* Start with the prefix path (which is known to be under PATH_MAX limit */
    snprintf(path, PATH_MAX, "%s", prefix_path);
    path_length = strlen(prefix_path); /* Start with the prefix path length */

    /* Process directory components in filename */
    dir_component = strtok(filename_copy, PYI_SEPSTR);
    while (dir_component != NULL) {
        /* Update and verify path length */
        path_length += strlen(dir_component) + strlen(PYI_SEPSTR);
        if (path_length >= PATH_MAX - 1) {
            return -1;
        }

        /* Update path */
        strcat(path, PYI_SEPSTR);
        strcat(path, dir_component);

        /* Look for next directory component, to ensure that our current
         * path is not the final filename. */
        dir_component = strtok(NULL, PYI_SEPSTR);
        if (dir_component == NULL) {
            break;
        }

        /* Create path if necessary */
        if (pyi_path_exists(path) == 0) {
#ifdef _WIN32
            wchar_t path_w[PATH_MAX];
            pyi_win32_utils_from_utf8(path_w, path, PATH_MAX);
            if (pyi_win32_mkdir(path_w, pyi_ctx->security_descriptor) < 0) {
                return -1;
            }
#else
            if (mkdir(path, 0700) < 0) {
                return -1;
            }
#endif
        }
    }

    return 0;
}

/*
 * Copy the source file to destination, in chunkc of 4 kB. The parent
 * directory tree of the destination must file must already exist
 */
int
pyi_copy_file(const char *src_filename, const char *dest_filename)
{
    FILE *fp_in;
    FILE *fp_out ;
    char buffer[4096];
    size_t byte_count = 0;
    int error = 0;

    fp_in = pyi_path_fopen(src_filename, "rb");
    if (fp_in == NULL) {
        return -1;
    }

    fp_out = pyi_path_fopen(dest_filename, "wb");
    if (fp_out == NULL) {
        fclose(fp_in);
        return -1;
    }

    while (!feof(fp_in)) {
        /* Read chunk */
        byte_count = fread(buffer, 1, 4096, fp_in);
        if (byte_count <= 0) {
            /* No data left or error */
            if (ferror(fp_in)) {
                clearerr(fp_in);
                error = -1;
            }
            break;
        }

        /* Write chunk */
        byte_count = fwrite(buffer, 1, byte_count, fp_out);
        if (byte_count <= 0 || ferror(fp_out)) {
            clearerr(fp_out);
            error = -1;
            break;
        }
    }

    /* Copy permissions bits */
#ifndef WIN32
    if (1) {
        struct stat stat_buf;
        mode_t permissions;

        /* Always set user readable and user writable, and copy the rest
         * from the source file */
        permissions = S_IRUSR | S_IWUSR;
        if (stat(src_filename, &stat_buf) == 0) {
            permissions |= stat_buf.st_mode;
        }
        fchmod(fileno(fp_out), permissions);
    }
#endif

    fclose(fp_in);
    fclose(fp_out);

    return error;
}


/**********************************************************************\
 *                  Shared library loading/unloading                  *
\**********************************************************************/
#ifdef _WIN32

/* Load shared/dynamic library */
dylib_t
pyi_utils_dlopen(const char *filename)
{
    wchar_t *filename_w;
    dylib_t handle;

    /* Convert UTF-8 to wide-char */
    filename_w = pyi_win32_utils_from_utf8(NULL, filename, 0);

    /* Load shared library */
    handle = LoadLibraryExW(filename_w, NULL, LOAD_WITH_ALTERED_SEARCH_PATH);

    free(filename_w);

    return handle;
}

/* Unload shared library by closing its handle */
int
pyi_utils_dlclose(dylib_t handle)
{
    return FreeLibrary(handle) ? 0 : -1; /* true/false -> 0/-1 */
}

#else /* ifdef _WIN32 */

dylib_t
pyi_utils_dlopen(const char *filename)
{
    int flags = RTLD_NOW | RTLD_GLOBAL;

#ifdef AIX
    /* Append the RTLD_MEMBER to the open mode for 'dlopen()'
     * in order to load shared object member from library. */
    flags |= RTLD_MEMBER;
#endif

    return dlopen(filename, flags);
}

int
pyi_utils_dlclose(dylib_t handle)
{
    return dlclose(handle);
}

#endif /* ifdef _WIN32 */


/**********************************************************************\
 *                  Child process spawning (onefile)                  *
\**********************************************************************/
#ifdef _WIN32

static BOOL WINAPI
_pyi_win32_console_ctrl(DWORD dwCtrlType)
{
    /* Due to different handling of VS() macro in MSVC and mingw gcc, the
     * former requires the name variable below to be available even in
     * non-debug builds (where VS() is no-op), while the latter complains
     * about the unused variable. So put everything under ifdef guard to
     * appease both. */
#if defined(LAUNCH_DEBUG)
    /* https://docs.microsoft.com/en-us/windows/console/handlerroutine */
    static const char *name_map[] = {
        "CTRL_C_EVENT", // 0
        "CTRL_BREAK_EVENT", // 1
        "CTRL_CLOSE_EVENT", // 2
        NULL,
        NULL,
        "CTRL_LOGOFF_EVENT", // 5
        "CTRL_SHUTDOWN_EVENT" // 6
    };
    const char *name = (dwCtrlType >= 0 && dwCtrlType <= 6) ? name_map[dwCtrlType] : NULL;

    /* NOTE: in case of CTRL_CLOSE_EVENT, CTRL_LOGOFF_EVENT, or
     * CTRL_SHUTDOWN_EVENT, the following message may not be printed to
     * console anymore. As per MSDN, the internal console cleanup routine
     * might have already been executed, preventing console functions
     * from working reliably. See Remarks section at:
     * https://docs.microsoft.com/en-us/windows/console/setconsolectrlhandler */
    VS("LOADER: received console control signal %d (%s)!\n", dwCtrlType, name ? name : "unknown");
#endif /* defined(LAUNCH_DEBUG) */

    /* Handle Ctrl+C and Ctrl+Break signals immediately. By returning TRUE,
     * their default handlers (which would call ExitProcess()) are not
     * called, so we are effectively suppressing the signal here, while
     * letting the child process (who also received it) handle it as they
     * see it fit. */
    if (dwCtrlType == CTRL_C_EVENT || dwCtrlType == CTRL_BREAK_EVENT) {
        return TRUE;
    }

    /* Delay the inevitable for as long as we can. The same signal should
     * also be received by the child process (as it is in the same process
     * group as the parent), which will terminate (after optionally
     * processing the signal, if python code installed its own handler).
     * Therefore, we just wait here "forever" (compared to OS-imposed
     * timeout for signal handling) to buy time for the child process to
     * terminate and for the main thread of this (parent) process to
     * perform the cleanup (sidenote: this handler is executed in a
     * separate thread). So this thread is terminated either when the
     * main thread of the process finishes and the program exits
     * (gracefully), or when the time runs out and the OS kills everything (see
     * https://docs.microsoft.com/en-us/windows/console/handlerroutine#timeouts). */
    Sleep(20000);
    return TRUE;
}

static HANDLE
_pyi_get_stream_handle(FILE *stream)
{
    HANDLE handle = (void *)_get_osfhandle(fileno(stream));
    /* When stdin, stdout, and stderr are not associated with a stream
     * (e.g., Windows application without console), _fileno() returns
     * special value -2. Therefore, call to _get_osfhandle() returns
     * INVALID_HANDLE_VALUE. If we caled _get_osfhandle() with 0, 1, or 2
     * instead of the result of _fileno(), _get_osfhandle() would also
     * return -2 when the file descriptor is not associated with the
     * stream. But because we take the _fileno() route, we need to handle
     * only INVALID_HANDLE_VALUE (= -1).
     * See: https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/get-osfhandle */
    if (handle == INVALID_HANDLE_VALUE) {
        return NULL;
    }
    return handle;
}

int
pyi_utils_create_child(PYI_CONTEXT *pyi_ctx)
{
    SECURITY_ATTRIBUTES security_attributes;
    STARTUPINFOW startup_info;
    PROCESS_INFORMATION process_info;
    wchar_t executable_filename_w[PATH_MAX];
    bool succeeded;
    DWORD child_exitcode;

    /* TODO is there a replacement for this conversion or just use wchar_t everywhere? */
    /* Convert file name to wchar_t from utf8. */
    pyi_win32_utils_from_utf8(executable_filename_w, pyi_ctx->executable_filename, PATH_MAX);

    /* Set up console ctrl handler; the call returns non-zero on success */
    if (SetConsoleCtrlHandler(_pyi_win32_console_ctrl, TRUE) == 0) {
        VS("LOADER: failed to install console ctrl handler!\n");
    }

    VS("LOADER: setting up to run child\n");

    security_attributes.nLength = sizeof(security_attributes);
    security_attributes.lpSecurityDescriptor = NULL;
    security_attributes.bInheritHandle = TRUE;

    GetStartupInfoW(&startup_info);
    startup_info.lpReserved = NULL;
    startup_info.lpDesktop = NULL;
    startup_info.lpTitle = NULL;
    startup_info.dwFlags = STARTF_USESTDHANDLES | STARTF_USESHOWWINDOW;
    startup_info.wShowWindow = SW_NORMAL;
    startup_info.hStdInput = _pyi_get_stream_handle(stdin);
    startup_info.hStdOutput = _pyi_get_stream_handle(stdout);
    startup_info.hStdError = _pyi_get_stream_handle(stderr);

    VS("LOADER: creating child process\n");

    succeeded = CreateProcessW(
        executable_filename_w, /* lpApplicationName */
        GetCommandLineW(), /* lpCommandLine */
        &security_attributes, /* lpProcessAttributes */
        NULL, /* lpThreadAttributes */
        TRUE, /* bInheritHandles */
        0, /* dwCreationFlags */
        NULL, /* lpEnvironment */
        NULL, /* lpCurrentDirectory */
        &startup_info, /* lpStartupInfo */
        &process_info /* lpProcessInformation */
    );
    if (succeeded) {
        VS("LOADER: waiting for child process to finish...\n");
        WaitForSingleObject(process_info.hProcess, INFINITE);
        GetExitCodeProcess(process_info.hProcess, &child_exitcode);
        return child_exitcode;
    }

    FATAL_WINERROR("CreateProcessW", "Failed to create child process!\n");
    return -1;
}

#else /* ifdef _WIN32 */

#if !defined(__APPLE__)

int
pyi_utils_set_library_search_path(const char *path)
{
    /* On AIX, LIBPATH is used to set dynamic library search path. On
     * other POSIX platforms (other than macOS), LD_LIBRARY_PATH is used. */
#ifdef AIX
    const char *variable_name = "LIBPATH";
    const char *variable_name_copy = "LIBPATH_ORIG";
#else
    const char *variable_name = "LD_LIBRARY_PATH";
    const char *variable_name_copy = "LD_LIBRARY_PATH_ORIG";
#endif

    char *orig_library_path = NULL;

    int rc = 0;

    /* Try retrieving the original value of the library-path environment
     * variable. */
    orig_library_path = pyi_getenv(variable_name);
    if (orig_library_path) {
        char *new_library_path;
        int new_library_path_length;

        /* Variable is set; store a copy (*_ORIG environment variable),
         * so that it can be restored, if necessary. */
        VS("LOADER: setting %s=%s\n", variable_name_copy, orig_library_path);
        pyi_setenv(variable_name_copy, orig_library_path);

        /* Compute the length of the new environment variable value:
         * given path + separator + original value + terminating NULL. */
        new_library_path_length = strlen(orig_library_path) + strlen(path) + 2;
        new_library_path = malloc(new_library_path_length);
        if (new_library_path == NULL) {
            rc = -1; /* Allocation failed */
        } else {
            snprintf(new_library_path, new_library_path_length, "%s:%s", path, orig_library_path);
            VS("LOADER: setting %s=%s\n", variable_name, new_library_path);
            rc = pyi_setenv(variable_name, new_library_path);
            free(new_library_path);
        }

        free(orig_library_path);
    } else {
        /* Variable not set; the new search path should contain just the
         * given path. */
        VS("LOADER: setting %s=%s\n", variable_name, path);
        rc = pyi_setenv(variable_name, path);
    }

    return rc;
}

#endif /* !defined(__APPLE__) */

/*
 * If the program is activated by a systemd socket, systemd will set
 * LISTEN_PID, LISTEN_FDS environment variable for that process.
 *
 * LISTEN_PID is set to the pid of the parent process of bootloader,
 * which is forked by systemd.
 *
 * Bootloader will duplicate LISTEN_FDS to child process, but the
 * LISTEN_PID environment variable remains unchanged.
 *
 * Here we change the LISTEN_PID to the child pid in child process.
 * So the application can detect it and use the LISTEN_FDS created
 * by systemd.
 */
static int
_pyi_set_systemd_env()
{
    const char *env_var_name = "LISTEN_PID";
    char *value;

    value = pyi_getenv(env_var_name);
    if (value != NULL) {
        /* 32 characters should be enough to accommodate the largest
         * value unsigned 64-bit integer (2^64 - 1), which takes up 20
         * characters. Even on contemporary 64-bit linux systems, PID
         * values have theoretical limit of 2^22, so there is a lot of
         * headroom here...   */
        char pid_str[32];

        free(value); /* Free the copy of original value, which we do not need. */

        snprintf(pid_str, 32, "%ld", (unsigned long)getpid());
        return pyi_setenv(env_var_name, pid_str);
    }

    return 0;
}

static void
_ignoring_signal_handler(int signum)
{
    /* Ignore the signal. Avoid generating debug messages as per
     * explanation in _signal_handler(). */
    (void)signum; /* Supress unused argument warnings */
}

static void
_signal_handler(int signum)
{
    /* Forward signal to the child. Avoid generating debug messages, as
     * functions involved are generally not signal safe. Furthermore, it
     * may result in endless spamming of SIGPIPE, as reported and
     * diagnosed in #5270. */
    kill(global_pyi_ctx->child_pid, signum);
}

/* Start frozen application in a subprocess. The frozen application runs
 * in a subprocess. */
int
pyi_utils_create_child(PYI_CONTEXT *pyi_ctx)
{
    pid_t pid = 0;
    int rc = 0;
    int wait_rc = -1;

    /* As indicated in signal(7), signal numbers range from 1-31 (standard)
     * and 32-64 (Linux real-time). */
    const size_t num_signals = 65;

    sighandler_t handler;
    int signum;

    /* macOS: Apple Events handling */
#if defined(__APPLE__) && defined(WINDOWED)
    /* Initialize pyi_argc and pyi_argv with original argc and argv.
     * Do this regardless of argv-emulation setting, because
     * pyi_utils_initialize_args() also filters out -psn_xxx argument. */
    if (pyi_utils_initialize_args(pyi_ctx, pyi_ctx->argc, pyi_ctx->argv) < 0) {
        goto cleanup;
    }

    /* Install Apple Event handlers */
    pyi_ctx->ae_ctx = pyi_apple_install_event_handlers(pyi_ctx);
    if (pyi_ctx->ae_ctx == NULL) {
        goto cleanup;
    }

    /* argv emulation; do a short (250 ms) cycle of Apple Events processing
     * before bringing up the child process */
    if (pyi_ctx->macos_argv_emulation) {
        pyi_apple_process_events(pyi_ctx->ae_ctx, 0.25);  /* short timeout (250 ms) */
    }
#endif

    pid = fork();
    if (pid < 0) {
        VS("LOADER: failed to fork child process: %s\n", strerror(errno));
        goto cleanup;
    }

    /* Child code. */
    if (pid == 0) {
        /* Replace process by starting a new application. */
        /* If modified arguments (pyi_ctx->pyi_argv) are available, use
         * those. Otherwise, use the original pyi_ctx->argv. */
        char *const *argv = (pyi_ctx->pyi_argv != NULL) ? pyi_ctx->pyi_argv : pyi_ctx->argv;

        if (_pyi_set_systemd_env() != 0) {
            VS("WARNING: application is started by systemd socket, but we cannot set proper LISTEN_PID on it.\n");
        }

        if (execvp(pyi_ctx->executable_filename, argv) < 0) {
            VS("Failed to exec: %s\n", strerror(errno));
            goto cleanup;
        }

        /* NOTREACHED */
    }

    /* From here to end-of-function is parent code (since the child exec'd).
     * The exception is the `cleanup` block that frees argv_pyi; in the child,
     * wait_rc is -1, so the child exit code checking is skipped. */

    pyi_ctx->child_pid = pid;
    handler = pyi_ctx->ignore_signals ? &_ignoring_signal_handler : &_signal_handler;

    /* Redirect all signals received by parent to child process. */
    if (pyi_ctx->ignore_signals) {
        VS("LOADER: Ignoring all signals in parent\n");
    } else {
        VS("LOADER: Registering signal handlers\n");
    }

    for (signum = 0; signum < num_signals; ++signum) {
        /* Don't mess with SIGCHLD/SIGCLD; it affects our ability
         * to wait() for the child to exit. Similarly, do not change
         * don't change SIGTSP handling to allow Ctrl-Z */
        if (signum != SIGCHLD && signum != SIGCLD && signum != SIGTSTP) {
            signal(signum, handler);
        }
    }

#if defined(__APPLE__) && defined(WINDOWED)
    /* macOS: forward events to child */
    do {
        /* The below loop will iterate about once every second on Apple,
         * waiting on the event queue most of that time. */
        wait_rc = waitpid(pyi_ctx->child_pid, &rc, WNOHANG);
        if (wait_rc == 0) {
            /* Check if we have a pending event that we need to forward... */
            if (pyi_apple_has_pending_event(pyi_ctx->ae_ctx)) {
                /* Attempt to re-send the pending event after 0.5 second delay. */
                if (pyi_apple_send_pending_event(pyi_ctx->ae_ctx, 0.5) != 0) {
                    /* Do not process additional events until the pending one
                     * is successfully forwarded (or cleaned up by error). */
                    continue;
                }
            }
            /* Wait for and process AppleEvents with a 1-second timeout, forwarding
             * events to the child. */
            pyi_apple_process_events(pyi_ctx->ae_ctx, 1.0);  /* long timeout (1 sec) */
        }
    } while (!wait_rc);

    /* Check if we have a pending event to forward (for diagnostics) */
    if (pyi_apple_has_pending_event(pyi_ctx->ae_ctx)) {
        VS("LOADER [AppleEvent]: Child terminated before pending event could be forwarded!\n");
        pyi_apple_cleanup_pending_event(pyi_ctx->ae_ctx);
    }

    /* Uninstall event handlers */
    pyi_apple_uninstall_event_handlers(&pyi_ctx->ae_ctx);
#else
    wait_rc = waitpid(pyi_ctx->child_pid, &rc, 0);
#endif

    if (wait_rc < 0) {
        VS("LOADER: failed to wait for child process: %s\n", strerror(errno));
    }

    /* When child process exited, reset signal handlers to default values. */
    VS("LOADER: restoring signal handlers\n");
    for (signum = 0; signum < num_signals; ++signum) {
        signal(signum, SIG_DFL);
    }

cleanup:
    /* Clean up the modified copy of command-line arguments (currently
     * applicable only to macOS windowed bootloader builds). */
#if defined(__APPLE__) && defined(WINDOWED)
    pyi_utils_free_args(pyi_ctx);
#endif

    /* Either wait() failed, or we jumped to `cleanup` and
     * didn't wait() at all. Either way, exit with error,
     * because rc does not contain a valid process exit code. */
    if (wait_rc < 0) {
        VS("LOADER: exiting early\n");
        return 1;
    }

    if (WIFEXITED(rc)) {
        VS("LOADER: returning child exit status %d\n", WEXITSTATUS(rc));
        return WEXITSTATUS(rc);
    }

    /* Process ended abnormally */
    pyi_ctx->child_signalled = WIFSIGNALED(rc);
    if (pyi_ctx->child_signalled) {
        pyi_ctx->child_signal = WTERMSIG(rc);
        VS("LOADER: child received signal %d; storing for re-raise after cleanup...\n", pyi_ctx->child_signal);
    }
    return 1;
}

#endif /* _WIN32 */


/**********************************************************************\
 *                 Argument filtering and modification                *
\**********************************************************************/
/* This is applicable only to POSIX systems */
#ifndef _WIN32

/*
 * Initialize private pyi_argc and pyi_argv from the given argc and
 * argv by creating a deep copy. The resulting pyi_argc and pyi_argv
 * can be retrieved directly from PYI_CONTEXT structure, and are
 * freed/cleaned-up by calling pyi_utils_free_args().
 *
 * The pyi_argv contains pyi_argv + 1 elements, with the last element
 * being NULL (i.e., it is execv-compatible NULL-terminated array).
 *
 * On macOS, this function filters out the -psnxxx argument that is
 * passed to executable when .app bundle is launched from Finder:
 * https://stackoverflow.com/questions/10242115/os-x-strange-psn-command-line-parameter-when-launched-from-finder
 */
int pyi_utils_initialize_args(PYI_CONTEXT *pyi_ctx, const int argc, char *const argv[])
{
    int i;

    pyi_ctx->pyi_argc = 0;
    pyi_ctx->pyi_argv = (char**)calloc(argc + 1, sizeof(char*));
    if (!pyi_ctx->pyi_argv) {
        FATALERROR("LOADER: failed to allocate pyi_argv: %s\n", strerror(errno));
        return -1;
    }

    for (i = 0; i < argc; i++) {
        char *tmp;

        /* Filter out -psnxxx argument that is used on macOS to pass
         * unique process serial number (PSN) to .app bundles launched
         * via Finder. */
#if defined(__APPLE__) && defined(WINDOWED)
        if (strstr(argv[i], "-psn") == argv[i]) {
            continue;
        }
#endif

        /* Copy the argument */
        tmp = strdup(argv[i]);
        if (!tmp) {
            FATALERROR("LOADER: failed to strdup argv[%d]: %s\n", i, strerror(errno));
            /* If we cannot allocate basic amounts of memory at this critical point,
             * we should probably just give up. */
            return -1;
        }
        pyi_ctx->pyi_argv[pyi_ctx->pyi_argc++] = tmp;
    }

    return 0;
}

/*
 * Append given argument to private pyi_argv and increment pyi_argc.
 * The pyi_argv array is reallocated accordingly.
 *
 * Returns 0 on success, -1 on failure (due to failed array reallocation).
 * On failure, pyi_argv and pyi_argc remain unchanged.
 */
int pyi_utils_append_to_args(PYI_CONTEXT *pyi_ctx, const char *arg)
{
    char **new_pyi_argv;
    char *arg_copy;

    /* Make a copy of new argument */
    arg_copy = strdup(arg);
    if (!arg_copy) {
        return -1;
    }

    /* Reallocate pyi_argv array, making space for new argument plus
     * terminating NULL */
    new_pyi_argv = (char**)realloc(pyi_ctx->pyi_argv, (pyi_ctx->pyi_argc + 2) * sizeof(char *));
    if (!new_pyi_argv) {
        free(arg_copy);
        return -1;
    }
    pyi_ctx->pyi_argv = new_pyi_argv;

    /* Store new argument */
    pyi_ctx->pyi_argv[pyi_ctx->pyi_argc++] = arg_copy;
    pyi_ctx->pyi_argv[pyi_ctx->pyi_argc] = NULL;

    return 0;
}

/*
 * Free/clean-up the private arguments (pyi_argv).
 */
void pyi_utils_free_args(PYI_CONTEXT *pyi_ctx)
{
    /* Free each entry */
    int i;
    for (i = 0; i < pyi_ctx->pyi_argc; i++) {
        free(pyi_ctx->pyi_argv[i]);
    }

    /* Free the array itself */
    free(pyi_ctx->pyi_argv);

    /* Clean-up the variables, just in case */
    pyi_ctx->pyi_argc = 0;
    pyi_ctx->pyi_argv = NULL;
}

#endif /* ifndef _WIN32 */


/**********************************************************************\
 *                       Magic pattern scanning                       *
\**********************************************************************/
/*
 * The base for MAGIC pattern(s) used within the bootloader. The actual
 * pattern should be programmatically constructed by copying this
 * array to a buffer and adjusting the fourth byte. This way, we avoid
 * storing the actual pattern in the executable, which would produce
 * false-positive matches when the executable is scanned.
 */
const unsigned char MAGIC_BASE[8] = {
    'M', 'E', 'I', 000,
    013, 012, 013, 016
};

/*
 * Perform full back-to-front scan of the given file and search for the
 * specified MAGIC pattern.
 *
 * Returns offset within the file if MAGIC pattern is found, 0 otherwise.
 */
uint64_t
pyi_utils_find_magic_pattern(FILE *fp, const unsigned char *magic, size_t magic_len)
{
    static const int SEARCH_CHUNK_SIZE = 8192;
    unsigned char *buffer = NULL;
    uint64_t start_pos, end_pos;
    uint64_t offset = 0;  /* return value */

    /* Allocate the read buffer */
    buffer = malloc(SEARCH_CHUNK_SIZE);
    if (!buffer) {
        VS("LOADER: failed to allocate read buffer (%d bytes)!\n", SEARCH_CHUNK_SIZE);
        goto cleanup;
    }

    /* Determine file size */
    if (pyi_fseek(fp, 0, SEEK_END) < 0) {
        VS("LOADER: failed to seek to the end of the file!\n");
        goto cleanup;
    }
    end_pos = pyi_ftell(fp);

    /* Sanity check */
    if (end_pos < magic_len) {
        VS("LOADER: file is too short to contain magic pattern!\n");
        goto cleanup;
    }

    /* Search the file back to front, in overlapping SEARCH_CHUNK_SIZE
     * chunks. */
    do {
        size_t chunk_size, i;
        start_pos = (end_pos >= SEARCH_CHUNK_SIZE) ? (end_pos - SEARCH_CHUNK_SIZE) : 0;
        chunk_size = (size_t)(end_pos - start_pos);

        /* Is the remaining chunk large enough to hold the pattern? */
        if (chunk_size < magic_len) {
            break;
        }

        /* Read the chunk */
        if (pyi_fseek(fp, start_pos, SEEK_SET) < 0) {
            VS("LOADER: failed to seek to the offset 0x%" PRIX64 "!\n", start_pos);
            goto cleanup;
        }
        if (fread(buffer, 1, chunk_size, fp) != chunk_size) {
            VS("LOADER: failed to read chunk (%zd bytes)!\n", chunk_size);
            goto cleanup;
        }

        /* Scan the chunk */
        for (i = chunk_size - magic_len + 1; i > 0; i--) {
            if (memcmp(buffer + i -1, magic, magic_len) == 0) {
                offset = start_pos + i - 1;
                goto cleanup;
            }
        }

        /* Adjust search location for next chunk; ensure proper overlap */
        end_pos = start_pos + magic_len - 1;
    } while (start_pos > 0);

cleanup:
    free(buffer);

    return offset;
}
