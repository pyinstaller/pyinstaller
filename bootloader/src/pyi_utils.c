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
#if defined(__APPLE__) && defined(WINDOWED)
    #include <Carbon/Carbon.h>  /* AppleEventsT */
    #include <ApplicationServices/ApplicationServices.h> /* GetProcessForPID, etc */
    /* Not declared in modern headers but exists in Carbon libs since time immemorial
     * See: https://applescriptlibrary.files.wordpress.com/2013/11/apple-events-programming-guide.pdf */
    extern Boolean ConvertEventRefToEventRecord(EventRef inEvent, EventRecord *outEvent);
#endif

/*
 * Function 'mkdtemp' (make temporary directory) is missing on some *nix platforms:
 * - On Solaris function 'mkdtemp' is missing.
 * - On AIX 5.2 function 'mkdtemp' is missing. It is there in version 6.1 but we don't know
 *   the runtime platform at compile time, so we always include our own implementation on AIX.
 */
#if defined(SUNOS) || defined(AIX) || defined(HPUX)
    #if !defined(HAVE_MKDTEMP)
    #include "mkdtemp.h"
    #endif
#endif

/* PyInstaller headers. */
#include "pyi_global.h"
#include "pyi_path.h"
#include "pyi_archive.h"
#include "pyi_utils.h"
#include "pyi_win32_utils.h"

/*
 *  global variables that are used to copy argc/argv, so that PyIstaller can manipulate them
 *  if need be.  One case in which the incoming argc/argv is manipulated is in the case of
 *  Apple/Windowed, where we watch for AppleEvents in order to add files to the command line.
 *  (this is argv_emulation).  These variables must be of file global scope to be able to
 *  be accessed inside of the AppleEvents handlers.
 */
static char **argv_pyi = NULL;
static int argc_pyi = 0;

// some platforms do not provide strnlen
#ifndef HAVE_STRNLEN
size_t
strnlen(const char *str, size_t n)
{
    const char *stop = (char *)memchr(str, '\0', n);
    return stop ? stop - str : n;
}
#endif

// some platforms do not provide strndup
#ifndef HAVE_STRNDUP
char *
strndup(const char * str, size_t n)
{
    char *ret = NULL;
    size_t len = strnlen(str, n);
    ret = (char *)malloc(len + 1);
    if (ret == NULL) return NULL;
    ret[len] = '\0';
    return (char *)memcpy(ret, str, len);
}
#endif


char *
pyi_strjoin(const char *first, const char *sep, const char *second){
    /* join first and second string, using sep as separator.
     * any of them may be either a null-terminated string or NULL.
     * sep will be only used if first and second string are not empty.
     * returns a null-terminated string which the caller is responsible
     * for freeing. Returns NULL if memory could not be allocated.
     */
    size_t first_len, sep_len, second_len;
    char *result;
    first_len = first ? strlen(first) : 0;
    sep_len = sep ? strlen(sep) : 0;
    second_len = second ? strlen(second) : 0;
    result = malloc(first_len + sep_len + second_len + 1);
    if (!result) {
        return NULL;
    }
    *result = '\0';
    if (first_len) {
        strcat(result, first);
    }
    if (sep_len && first_len && second_len) {
        strcat(result, sep);
    }
    if (second_len) {
        strcat(result, second);
    }
    return result;
}

/* Return string copy of environment variable. */
char *
pyi_getenv(const char *variable)
{
    char *env = NULL;

#ifdef _WIN32
    wchar_t * wenv = NULL;
    wchar_t * wvar = NULL;
    wchar_t buf1[PATH_MAX], buf2[PATH_MAX];
    DWORD rc;

    wvar = pyi_win32_utils_from_utf8(NULL, variable, 0);
    rc = GetEnvironmentVariableW(wvar, buf1, sizeof(buf1));

    if (rc > 0) {
        wenv = buf1;
        /* Expand environment variables like %VAR% in value. */
        rc = ExpandEnvironmentStringsW(wenv, buf2, sizeof(buf2));

        if (rc > 0) {
            wenv = buf1;
        }
    }

    if (wenv) {
        env = pyi_win32_utils_to_utf8(NULL, wenv, 0);
    }
#else /*
       * ifdef _WIN32
       * Standard POSIX function.
       */
    env = getenv(variable);
#endif /* ifdef _WIN32 */

    /* If the Python program we are about to run invokes another PyInstaller
     * one-file program as subprocess, this subprocess must not be fooled into
     * thinking that it is already unpacked. Therefore, PyInstaller deletes
     * the _MEIPASS2 variable from the environment in pyi_main().
     *
     * However, on some platforms (e.g. AIX) the Python function 'os.unsetenv()'
     * does not always exist. In these cases we cannot delete the _MEIPASS2
     * environment variable from Python but only set it to the empty string.
     * The code below takes into account that a variable may exist while its
     * value is only the empty string.
     *
     * Return copy of string to avoid modification of the process environment.
     */
    return (env && env[0]) ? strdup(env) : NULL;
}

/* Set environment variable. */
int
pyi_setenv(const char *variable, const char *value)
{
    int rc;

#ifdef _WIN32
    wchar_t * wvar, *wval;

    wvar = pyi_win32_utils_from_utf8(NULL, variable, 0);
    wval = pyi_win32_utils_from_utf8(NULL, value, 0);

    // Not sure why, but SetEnvironmentVariableW() didn't work with _wtempnam()
    // Replaced it with _wputenv_s()
    rc = _wputenv_s(wvar, wval);

    free(wvar);
    free(wval);
#else
    rc = setenv(variable, value, true);
#endif
    return rc;
}

/* Unset environment variable. */
int
pyi_unsetenv(const char *variable)
{
    int rc;

#ifdef _WIN32
    wchar_t * wvar;
    wvar = pyi_win32_utils_from_utf8(NULL, variable, 0);
    rc = SetEnvironmentVariableW(wvar, NULL);
    free(wvar);
#else  /* _WIN32 */
    #if HAVE_UNSETENV
    rc = unsetenv(variable);
    #else /* HAVE_UNSETENV */
    rc = setenv(variable, "", true);
    #endif /* HAVE_UNSETENV */
#endif     /* _WIN32 */
    return rc;
}

#ifdef _WIN32

/* Resolve the runtime tmpdir path and build nested directories */
wchar_t
*pyi_build_temp_folder(char *runtime_tmpdir)
{
    wchar_t *wruntime_tmpdir;
    wchar_t wruntime_tmpdir_expanded[PATH_MAX];
    wchar_t *wruntime_tmpdir_abspath;
    wchar_t *cursor;
    wchar_t path_builder[PATH_MAX];
    DWORD rc;
    // Expand environment variables like %LOCALAPPDATA%
    wruntime_tmpdir = pyi_win32_utils_from_utf8(NULL, runtime_tmpdir, 0);
    if (!wruntime_tmpdir) {
        FATALERROR("LOADER: Failed to convert runtime-tmpdir to a wide string.\n");
        return NULL;
    }
    rc = ExpandEnvironmentStringsW(wruntime_tmpdir, wruntime_tmpdir_expanded,
                                   PATH_MAX);
    free(wruntime_tmpdir);
    if (!rc) {
        FATALERROR("LOADER: Failed to expand environment variables in the runtime-tmpdir.\n");
        return NULL;
    }
    // Get the absolute path
    if (pyi_win32_is_drive_root(wruntime_tmpdir_expanded)) {
        /* Disk drive (e.g., "c:"); do not attempt to call _wfullpath(), because it will return
           the current directory of this drive. So return a verbatim copy instead. */
        wruntime_tmpdir_abspath = _wcsdup(wruntime_tmpdir_expanded);
    } else {
        wruntime_tmpdir_abspath = _wfullpath(NULL, wruntime_tmpdir_expanded, PATH_MAX);
    }
    if (!wruntime_tmpdir_abspath) {
        FATALERROR("LOADER: Failed to obtain the absolute path of the runtime-tmpdir.\n");
        return NULL;
    }
    VS("LOADER: absolute runtime tmpdir is %ls\n", wruntime_tmpdir_abspath);
    // Create the directory path if it does not yet already exist (e.g.
    // %AppData%\NewFolder\NestedFolder)
    ZeroMemory(path_builder, PATH_MAX * sizeof(wchar_t));
    cursor = wcschr(wruntime_tmpdir_abspath, L'\\');
    while(cursor != NULL) {
        wcsncpy(path_builder, wruntime_tmpdir_abspath,
                cursor - wruntime_tmpdir_abspath + 1);
        CreateDirectoryW(path_builder, NULL);
        // We expect ERROR_ALREADY_EXISTS, ERROR_ACCESS_DENIED (if try to
        // create a drive when running as an admin), etc...
        cursor = wcschr(++cursor, L'\\');
    }
    // May not have a string terminated with \, so run CreateDirectoryW one
    // last time to handle that case
    CreateDirectoryW(wruntime_tmpdir_abspath, NULL);
    return wruntime_tmpdir_abspath;
}

/* TODO rename fuction and revisit */
int
pyi_get_temp_path(char *buffer, char *runtime_tmpdir)
{
    int i;
    wchar_t *wchar_ret;
    wchar_t prefix[16];
    wchar_t wchar_buffer[PATH_MAX];
    char *original_tmpdir;
    wchar_t *wruntime_tmpdir_abspath;
    DWORD rc;

    if (runtime_tmpdir != NULL) {
      /*
       * Get original TMP environment variable so it can be restored
       * after this is done.
       */
      original_tmpdir = pyi_getenv("TMP");
      /*
       * Set TMP to runtime_tmpdir for _wtempnam() later
       */
      wruntime_tmpdir_abspath = pyi_build_temp_folder(runtime_tmpdir);
      if (!wruntime_tmpdir_abspath) {
          return 0;
      }
      // Store in the TMP environment variable
      rc = _wputenv_s(L"TMP", wruntime_tmpdir_abspath);
      free(wruntime_tmpdir_abspath);
      if (rc) {
          FATALERROR("LOADER: Failed to set the TMP environment variable.\n");
          return 0;
      }
      VS("LOADER: Successfully resolved the specified runtime-tmpdir\n");
    }

    GetTempPathW(PATH_MAX, wchar_buffer);

    swprintf(prefix, 16, L"_MEI%d", getpid());

    /*
     * Windows does not have a race-free function to create a temporary
     * directory. Thus, we rely on _tempnam, and simply try several times
     * to avoid stupid race conditions.
     */
    for (i = 0; i < 5; i++) {
        /* TODO use race-free fuction - if any exists? */
        wchar_ret = _wtempnam(wchar_buffer, prefix);

        if (pyi_win32_mkdir(wchar_ret) == 0) {
            pyi_win32_utils_to_utf8(buffer, wchar_ret, PATH_MAX);
            free(wchar_ret);
            if (runtime_tmpdir != NULL) {
              /*
               * Restore TMP to what it was
               */
              if (original_tmpdir != NULL) {
                pyi_setenv("TMP", original_tmpdir);
                free(original_tmpdir);
              } else {
                pyi_unsetenv("TMP");
              }
            }
            return 1;
        }
        free(wchar_ret);
    }
    if (runtime_tmpdir != NULL) {
      /*
       * Restore TMP to what it was
       */
      if (original_tmpdir != NULL) {
        pyi_setenv("TMP", original_tmpdir);
        free(original_tmpdir);
      } else {
        pyi_unsetenv("TMP");
      }
    }
    return 0;
}

#else /* ifdef _WIN32 */

/* TODO Is this really necessary to test for temp path? Why not just use mkdtemp()? */
int
pyi_test_temp_path(char *buff)
{
    /*
     * If path does not end with directory separator - append it there.
     * On OSX the value from $TMPDIR ends with '/'.
     */
    if (buff[strlen(buff) - 1] != PYI_SEP) {
        strcat(buff, PYI_SEPSTR);
    }
    strcat(buff, "_MEIXXXXXX");

    if (mkdtemp(buff)) {
        return 1;
    }
    return 0;
}

/* TODO merge this function with windows version. */
static int
pyi_get_temp_path(char *buff, char *runtime_tmpdir)
{
    if (runtime_tmpdir != NULL) {
      strcpy(buff, runtime_tmpdir);
      if (pyi_test_temp_path(buff))
        return 1;
    } else {
      /* On OSX the variable TMPDIR is usually defined. */
      static const char *envname[] = {
          "TMPDIR", "TEMP", "TMP", 0
      };
      static const char *dirname[] = {
          "/tmp", "/var/tmp", "/usr/tmp", 0
      };
      int i;
      char *p;

      for (i = 0; envname[i]; i++) {
          p = pyi_getenv(envname[i]);

          if (p) {
              strcpy(buff, p);

              if (pyi_test_temp_path(buff)) {
                  return 1;
              }
          }
      }

      for (i = 0; dirname[i]; i++) {
          strcpy(buff, dirname[i]);

          if (pyi_test_temp_path(buff)) {
              return 1;
          }
      }
    }
    return 0;
}

#endif /* ifdef _WIN32 */

/*
 * Creates a temporany directory if it doesn't exists
 * and properly sets the ARCHIVE_STATUS members.
 */
int
pyi_create_temp_path(ARCHIVE_STATUS *status)
{
    char *runtime_tmpdir = NULL;

    if (status->has_temp_directory != true) {
        runtime_tmpdir = pyi_arch_get_option(status, "pyi-runtime-tmpdir");
        if(runtime_tmpdir != NULL) {
          VS("LOADER: Found runtime-tmpdir %s\n", runtime_tmpdir);
        }

        if (!pyi_get_temp_path(status->temppath, runtime_tmpdir)) {
            FATALERROR("INTERNAL ERROR: cannot create temporary directory!\n");
            return -1;
        }
        /* Set flag that temp directory is created and available. */
        status->has_temp_directory = true;
    }
    return 0;
}

/* TODO merge unix/win versions of remove_one() and pyi_remove_temp_path() */
#ifdef _WIN32
static void
remove_one(wchar_t *wfnm, size_t pos, struct _wfinddata_t wfinfo)
{
    char fnm[PATH_MAX + 1];

    if (wcscmp(wfinfo.name, L".") == 0  || wcscmp(wfinfo.name, L"..") == 0) {
        return;
    }
    wfnm[pos] = PYI_NULLCHAR;
    wcscat(wfnm, wfinfo.name);

    if (wfinfo.attrib & _A_SUBDIR) {
        /* Use recursion to remove subdirectories. */
        pyi_win32_utils_to_utf8(fnm, wfnm, PATH_MAX);
        pyi_remove_temp_path(fnm);
    }
    else if (_wremove(wfnm)) {
        /* HACK: Possible concurrency issue... spin a little while */
        Sleep(100);
        _wremove(wfnm);
    }
}

/* TODO Find easier and more portable implementation of removing directory recursively. */
/*     e.g. */
void
pyi_remove_temp_path(const char *dir)
{
    wchar_t wfnm[PATH_MAX + 1];
    wchar_t wdir[PATH_MAX + 1];
    struct _wfinddata_t wfinfo;
    intptr_t h;
    size_t dirnmlen;

    pyi_win32_utils_from_utf8(wdir, dir, PATH_MAX);
    wcscpy(wfnm, wdir);
    dirnmlen = wcslen(wfnm);

    if (wfnm[dirnmlen - 1] != L'/' && wfnm[dirnmlen - 1] != L'\\') {
        wcscat(wfnm, L"\\");
        dirnmlen++;
    }
    wcscat(wfnm, L"*");
    h = _wfindfirst(wfnm, &wfinfo);

    if (h != -1) {
        remove_one(wfnm, dirnmlen, wfinfo);

        while (_wfindnext(h, &wfinfo) == 0) {
            remove_one(wfnm, dirnmlen, wfinfo);
        }
        _findclose(h);
    }
    _wrmdir(wdir);
}
#else /* ifdef _WIN32 */
static void
remove_one(char *pnm, int pos, const char *fnm)
{
    struct stat sbuf;

    if (strcmp(fnm, ".") == 0  || strcmp(fnm, "..") == 0) {
        return;
    }
    pnm[pos] = PYI_NULLCHAR;
    strcat(pnm, fnm);

    if (stat(pnm, &sbuf) == 0) {
        if (S_ISDIR(sbuf.st_mode) ) {
            /* Use recursion to remove subdirectories. */
            pyi_remove_temp_path(pnm);
        }
        else {
            unlink(pnm);
        }
    }
}

void
pyi_remove_temp_path(const char *dir)
{
    char fnm[PATH_MAX + 1];
    DIR *ds;
    struct dirent *finfo;
    int dirnmlen;

    /* Leave 1 char for PY_SEP if needed */
    strncpy(fnm, dir, PATH_MAX);
    dirnmlen = strlen(fnm);

    if (fnm[dirnmlen - 1] != PYI_SEP) {
        strcat(fnm, PYI_SEPSTR);
        dirnmlen++;
    }
    ds = opendir(dir);
    if (!ds) {
        return;
    }
    finfo = readdir(ds);

    while (finfo) {
        remove_one(fnm, dirnmlen, finfo->d_name);
        finfo = readdir(ds);
    }
    closedir(ds);
    rmdir(dir);
}
#endif /* ifdef _WIN32 */

/*
 * helper for extract2fs
 * which may try multiple places
 */
/* TODO find better name for function. */
FILE *
pyi_open_target(const char *path, const char* name_)
{

#ifdef _WIN32
    wchar_t wchar_buffer[PATH_MAX];
    struct _stat sbuf;
#else
    struct stat sbuf;
#endif
    char fnm[PATH_MAX];
    char name[PATH_MAX];
    char *dir;
    size_t len;

    if (snprintf(fnm, PATH_MAX, "%s", path) >= PATH_MAX ||
        snprintf(name, PATH_MAX, "%s", name_) >= PATH_MAX) {
        return NULL;
    }

    len = strlen(fnm);
    dir = strtok(name, PYI_SEPSTR);

    while (dir != NULL) {
        len += strlen(dir) + strlen(PYI_SEPSTR);
        /* Check if fnm does not exceed the buffer size */
        if (len >= PATH_MAX-1) {
            return NULL;
        }
        strcat(fnm, PYI_SEPSTR);
        strcat(fnm, dir);
        dir = strtok(NULL, PYI_SEPSTR);

        if (!dir) {
            break;
        }

#ifdef _WIN32
        pyi_win32_utils_from_utf8(wchar_buffer, fnm, PATH_MAX);

        if (_wstat(wchar_buffer, &sbuf) < 0) {
            pyi_win32_mkdir(wchar_buffer);
        }
#else

        if (stat(fnm, &sbuf) < 0) {
            mkdir(fnm, 0700);
        }
#endif
    }

#ifdef _WIN32
    pyi_win32_utils_from_utf8(wchar_buffer, fnm, PATH_MAX);

    if (_wstat(wchar_buffer, &sbuf) == 0) {
        OTHERERROR("WARNING: file already exists but should not: %s\n", fnm);
    }
#else

    if (stat(fnm, &sbuf) == 0) {
        OTHERERROR("WARNING: file already exists but should not: %s\n", fnm);
    }
#endif
    /*
     * pyi_path_fopen() wraps different fopen names. On Windows it uses
     * wide-character version of fopen.
     */
    return pyi_path_fopen(fnm, "wb");
}

/* Copy the file src to dst 4KB per time */
int
pyi_copy_file(const char *src, const char *dst, const char *filename)
{
    FILE *in = pyi_path_fopen(src, "rb");
    FILE *out = pyi_open_target(dst, filename);
    char buf[4096];
    size_t read_count = 0;
    int error = 0;

    if (in == NULL || out == NULL) {
        if (in) {
            fclose(in);
        }
        if (out) {
            fclose(out);
        }
        return -1;
    }

    while (!feof(in)) {
        read_count = fread(buf, 1, 4096, in);
        if (read_count <= 0 ) {
            if (ferror(in)) {
                clearerr(in);
                error = -1;
                break;
            }
        }
        else {
            size_t rc = fwrite(buf, 1, read_count, out);
            if (rc <= 0 || ferror(out)) {
                clearerr(out);
                error = -1;
                break;
            }
        }
    }
#ifndef WIN32
    fchmod(fileno(out), S_IRUSR | S_IWUSR | S_IXUSR);
#endif
    fclose(in);
    fclose(out);

    return error;
}

/* Load the shared dynamic library (DLL) */
dylib_t
pyi_utils_dlopen(const char *dllpath)
{

#ifdef _WIN32
    wchar_t * dllpath_w;
    dylib_t ret;
#else
    int dlopenMode = RTLD_NOW | RTLD_GLOBAL;
#endif

#ifdef AIX
    /* Append the RTLD_MEMBER to the open mode for 'dlopen()'
     * in order to load shared object member from library.
     */
    dlopenMode |= RTLD_MEMBER;
#endif

#ifdef _WIN32
    dllpath_w = pyi_win32_utils_from_utf8(NULL, dllpath, 0);
    ret = LoadLibraryExW(dllpath_w, NULL, LOAD_WITH_ALTERED_SEARCH_PATH);
    free(dllpath_w);
    return ret;
#else
    return dlopen(dllpath, dlopenMode);
#endif

}

/* TODO use pyi_utils_dlclose() when exiting. */
/* Unlink/Close the shared library.
 * Returns zero on success, a nonzero value on failure.
 *
 * Interesting fact: many debuggers link to attached libraries
 * too, therefore calling dlclose from within the bootloader
 * does **not** necessarily mean the library will be unloaded
 * if a debugger is attached. */
int
pyi_utils_dlclose(dylib_t dll)
{
#ifdef _WIN32
    /* FreeLibrary returns a nonzero value on success,
     * invert it to provide a common return value */
    return !FreeLibrary(dll);
#else
    return dlclose(dll);
#endif
}

/* ////////////////////////////////////////////////////////////////// */
/* TODO better merging of the following platform specific functions. */
/* ////////////////////////////////////////////////////////////////// */

#ifdef _WIN32

int
pyi_utils_set_environment(const ARCHIVE_STATUS *status)
{
    return 0;
}

int
pyi_utils_create_child(const char *thisfile, const ARCHIVE_STATUS* status,
                       const int argc, char *const argv[])
{
    SECURITY_ATTRIBUTES sa;
    STARTUPINFOW si;
    PROCESS_INFORMATION pi;
    int rc = 0;
    wchar_t buffer[PATH_MAX];

    /* TODO is there a replacement for this conversion or just use wchar_t everywhere? */
    /* Convert file name to wchar_t from utf8. */
    pyi_win32_utils_from_utf8(buffer, thisfile, PATH_MAX);

    /* the parent process should ignore all signals it can */
    signal(SIGABRT, SIG_IGN);
    signal(SIGINT, SIG_IGN);
    signal(SIGTERM, SIG_IGN);
    signal(SIGBREAK, SIG_IGN);

    VS("LOADER: Setting up to run child\n");
    sa.nLength = sizeof(sa);
    sa.lpSecurityDescriptor = NULL;
    sa.bInheritHandle = TRUE;
    GetStartupInfoW(&si);
    si.lpReserved = NULL;
    si.lpDesktop = NULL;
    si.lpTitle = NULL;
    si.dwFlags = STARTF_USESTDHANDLES | STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_NORMAL;
    si.hStdInput = (void*)_get_osfhandle(fileno(stdin));
    si.hStdOutput = (void*)_get_osfhandle(fileno(stdout));
    si.hStdError = (void*)_get_osfhandle(fileno(stderr));

    VS("LOADER: Creating child process\n");

    if (CreateProcessW(
            buffer,            /* Pointer to name of executable module. */
            GetCommandLineW(), /* pointer to command line string */
            &sa,               /* pointer to process security attributes */
            NULL,              /* pointer to thread security attributes */
            TRUE,              /* handle inheritance flag */
            0,                 /* creation flags */
            NULL,              /* pointer to new environment block */
            NULL,              /* pointer to current directory name */
            &si,               /* pointer to STARTUPINFO */
            &pi                /* pointer to PROCESS_INFORMATION */
            )) {
        VS("LOADER: Waiting for child process to finish...\n");
        WaitForSingleObject(pi.hProcess, INFINITE);
        GetExitCodeProcess(pi.hProcess, (unsigned long *)&rc);
    }
    else {
        FATAL_WINERROR("CreateProcessW", "Error creating child process!\n");
        rc = -1;
    }
    return rc;
}

#else /* ifdef _WIN32 */

static int
set_dynamic_library_path(const char* path)
{
    int rc = 0;
    char *env_var, *env_var_orig;
    char *new_path, *orig_path;

    #ifdef AIX
    /* LIBPATH is used to look up dynamic libraries on AIX. */
    env_var = "LIBPATH";
    env_var_orig = "LIBPATH_ORIG";
    #else
    /* LD_LIBRARY_PATH is used on other *nix platforms (except Darwin). */
    env_var = "LD_LIBRARY_PATH";
    env_var_orig = "LD_LIBRARY_PATH_ORIG";
    #endif /* AIX */

    /* keep original value in a new env var so the application can restore it
     * before forking subprocesses. This is important so that e.g. a forked
     * (system installed) ssh can find the matching (system installed) ssh
     * related libraries - not the potentially different versions of same libs
     * that we have bundled.
     */
    orig_path = pyi_getenv(env_var);
    if (orig_path) {
        pyi_setenv(env_var_orig, orig_path);
        VS("LOADER: %s=%s\n", env_var_orig, orig_path);
    }
    /* prepend our path to the original path, pyi_strjoin can deal with orig_path being NULL or empty string */
    new_path = pyi_strjoin(path, ":", orig_path);
    rc = pyi_setenv(env_var, new_path);
    VS("LOADER: %s=%s\n", env_var, new_path);
    free(new_path);
    return rc;
}

int
pyi_utils_set_environment(const ARCHIVE_STATUS *status)
{
    int rc = 0;

    #ifdef __APPLE__
    /* On Mac OS X we do not use environment variables DYLD_LIBRARY_PATH
     * or others to tell OS where to look for dynamic libraries.
     * There were some issues with this approach. In some cases some
     * system libraries were trying to load incompatible libraries from
     * the dist directory. For instance this was experienced with macprots
     * and PyQt applications.
     *
     * To tell the OS where to look for dynamic libraries we modify
     * .so/.dylib files to use relative paths to other dependend
     * libraries starting with @executable_path.
     *
     * For more information see:
     * http://blogs.oracle.com/dipol/entry/dynamic_libraries_rpath_and_mac
     * http://developer.apple.com/library/mac/#documentation/DeveloperTools/  \
     *     Conceptual/DynamicLibraries/100-Articles/DynamicLibraryUsageGuidelines.html
     */
    /* For environment variable details see 'man dyld'. */
    pyi_unsetenv("DYLD_FRAMEWORK_PATH");
    pyi_unsetenv("DYLD_FALLBACK_FRAMEWORK_PATH");
    pyi_unsetenv("DYLD_VERSIONED_FRAMEWORK_PATH");
    pyi_unsetenv("DYLD_LIBRARY_PATH");
    pyi_unsetenv("DYLD_FALLBACK_LIBRARY_PATH");
    pyi_unsetenv("DYLD_VERSIONED_LIBRARY_PATH");
    pyi_unsetenv("DYLD_ROOT_PATH");

    #else

    /* Set library path to temppath. This is only for onefile mode.*/
    if (status->temppath[0] != PYI_NULLCHAR) {
        rc = set_dynamic_library_path(status->temppath);
    }
    /* Set library path to homepath. This is for default onedir mode.*/
    else {
        rc = set_dynamic_library_path(status->homepath);
    }
    #endif /* ifdef __APPLE__ */

    return rc;
}

/*
 * If the program is actived by a systemd socket, systemd will set
 * LISTEN_PID, LISTEN_FDS environment variable for that process.
 *
 * LISTEN_PID is set to the pid of the parent process of bootloader,
 * which is forked by systemd.
 *
 * Bootloader will duplicate LISTEN_FDS to child process, but the
 * LISTEN_PID environment variable remains unchanged.
 *
 * Here we change the LISTEN_PID to the child pid in child process.
 * So the application can detecte it and use the LISTEN_FDS created
 * by systemd.
 */
int
set_systemd_env()
{
    const char * env_var = "LISTEN_PID";
    if(pyi_getenv(env_var) != NULL) {
        /* the ULONG_STRING_SIZE is roughly equal to log10(max number)
         * but can be calculated in compile time.
         * The idea is from an answer on stackoverflow,
         * https://stackoverflow.com/questions/8257714/
         */
        #define ULONG_STRING_SIZE (sizeof (unsigned long) * CHAR_BIT / 3 + 2)
        char pid_str[ULONG_STRING_SIZE];
        snprintf(pid_str, ULONG_STRING_SIZE, "%ld", (unsigned long)getpid());
        return pyi_setenv(env_var, pid_str);
    }
    return 0;
}

/* Remember child process id. It allows sending a signal to child process.
 * Frozen application always runs in a child process. Parent process is used
 * to setup environment for child process and clean the environment when
 * child exited.
 */
pid_t child_pid = 0;

static void
_ignoring_signal_handler(int signum)
{
    VS("LOADER: Ignoring signal %d\n", signum);
}

static void
_signal_handler(int signum)
{
    VS("LOADER: Forwarding signal %d to child pid %d\n", signum, child_pid);
    kill(child_pid, signum);
}

/* Start frozen application in a subprocess. The frozen application runs
 * in a subprocess.
 */
int
pyi_utils_create_child(const char *thisfile, const ARCHIVE_STATUS* status,
                       const int argc, char *const argv[])
{
    pid_t pid = 0;
    int rc = 0;
    int i;

    /* cause nonzero return unless this is overwritten
     * with a successful return code from wait() */
    int wait_rc = -1;

    /* As indicated in signal(7), signal numbers range from 1-31 (standard)
     * and 32-64 (Linux real-time). */
    const size_t num_signals = 65;

    sighandler_t handler;
    int ignore_signals;
    int signum;

    /* Initialize argv_pyi and argc_pyi */
    if (pyi_utils_initialize_args(argc, argv) < 0) {
        goto cleanup;
    }

    #if defined(__APPLE__) && defined(WINDOWED)
    pyi_process_apple_events(true /* short timeout (250 ms) */);
    #endif

    pid = fork();
    if (pid < 0) {
        VS("LOADER: failed to fork child process: %s\n", strerror(errno));
        goto cleanup;
    }

    /* Child code. */
    if (pid == 0) {
        /* Replace process by starting a new application. */
        if (set_systemd_env() != 0) {
            VS("WARNING: Application is started by systemd socket,"
               "but we can't set proper LISTEN_PID on it.\n");
        }
        if (execvp(thisfile, argv_pyi) < 0) {
            VS("Failed to exec: %s\n", strerror(errno));
            goto cleanup;
        }
        /* NOTREACHED */
    }

    /* From here to end-of-function is parent code (since the child exec'd).
     * The exception is the `cleanup` block that frees argv_pyi; in the child,
     * wait_rc is -1, so the child exit code checking is skipped. */

    child_pid = pid;
    ignore_signals = (pyi_arch_get_option(status, "pyi-bootloader-ignore-signals") != NULL);
    handler = ignore_signals ? &_ignoring_signal_handler : &_signal_handler;

    /* Redirect all signals received by parent to child process. */
    if (ignore_signals) {
        VS("LOADER: Ignoring all signals in parent\n");
    } else {
        VS("LOADER: Registering signal handlers\n");
    }
    for (signum = 0; signum < num_signals; ++signum) {
        // don't mess with SIGCHLD/SIGCLD; it affects our ability
        // to wait() for the child to exit
        // don't change SIGTSP handling to allow Ctrl-Z
        if (signum != SIGCHLD && signum != SIGCLD && signum != SIGTSTP) {
            signal(signum, handler);
        }
    }

    #if defined(__APPLE__) && defined(WINDOWED)
    /* MacOS code -- forward events to child! */
    do {
        /* The below loop will iterate about once every second on Apple,
         * waiting on the event queue most of that time. */
        wait_rc = waitpid(child_pid, &rc, WNOHANG);
        if (wait_rc == 0) {
            /* Child not done yet -- wait for and process AppleEvents with a
             * 1 second timeout, forwarding file-open events to the child. */
            pyi_process_apple_events(false /* long timeout (1 sec) */);
        }
    } while (!wait_rc);
    #else
    wait_rc = waitpid(child_pid, &rc, 0);
    #endif
    if (wait_rc < 0) {
        VS("LOADER: failed to wait for child process: %s\n", strerror(errno));
    }

    /* When child process exited, reset signal handlers to default values. */
    VS("LOADER: Restoring signal handlers\n");
    for (signum = 0; signum < num_signals; ++signum) {
        signal(signum, SIG_DFL);
    }

  cleanup:
    VS("LOADER: freeing args\n");
    pyi_utils_free_args();

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
    if (WIFSIGNALED(rc)) {
        VS("LOADER: re-raising child signal %d\n", WTERMSIG(rc));
        /* Mimick the signal the child received */
        raise(WTERMSIG(rc));
    }
    return 1;
}


#if !defined(__APPLE__)

/* Replace the current process with another instance of itself, i.e.,
 * restart the process in-place (exec() without fork()). Used on linux
 * and unix-like OSes to achieve single-process onedir execution mode.
 */
int pyi_utils_replace_process(const char *thisfile, const int argc, char *const argv[])
{
    int rc;

    /* Use helper to copy argv into NULL-terminated arguments array, argv_pyi. */
    if (pyi_utils_initialize_args(argc, argv) < 0) {
        return -1;
    }
    /* Replace the current executable image. */
    rc = execvp(thisfile, argv_pyi);
    /* This part is reached only if exec() failed. */
    if (rc < 0) {
        VS("Failed to exec: %s\n", strerror(errno));
    }
    return rc;
}

#endif /* !defined(__APPLE) */


/*
 * Initialize private argc_pyi and argv_pyi from the given argc and
 * argv by creating a deep copy. The resulting argc_pyi and argv_pyi
 * can be retrieved by pyi_utils_get_args() and are freed/cleaned-up by
 * pyi_utils_free_args().
 *
 * The argv_pyi contains argc_pyi + 1 elements, with the last element
 * being NULL (i.e., it is execv-compatible NULL-terminated array).
 *
 * On macOS, this function filters out the -psnxxx argument that is
 * passed to executable when .app bundle is launched from Finder:
 * https://stackoverflow.com/questions/10242115/os-x-strange-psn-command-line-parameter-when-launched-from-finder
 */
int pyi_utils_initialize_args(const int argc, char *const argv[])
{
    int i;

    argv_pyi = (char**)calloc(argc + 1, sizeof(char*));
    argc_pyi = 0;
    if (!argv_pyi) {
        FATALERROR("LOADER: failed to allocate argv_pyi: %s\n", strerror(errno));
        return -1;
    }

    for (i = 0; i < argc; i++) {
        char *tmp;

        /* Filter out -psnxxx argument that is used on macOS to pass
         * unique process serial number (PSN) to apps launched via Finder. */
        #if defined(__APPLE__) && defined(WINDOWED)
        if (strstr(argv[i], "-psn") == argv[i]) {
            continue;
        }
        #endif

        /* Copy the argument */
        tmp = strdup(argv[i]);
        if (!tmp) {
            FATALERROR("LOADER: failed to strdup argv[%d]: %s\n", i, strerror(errno));
            /* If we can't allocate basic amounts of memory at this critical point,
             * we should probably just give up. */
            return -1;
        }
        argv_pyi[argc_pyi++] = tmp;
    }

    return 0;
}

/*
 * Retrieve value of argc_pyi and the pointer to argv_pyi. The retrieved
 * arguments are originally the same as the ones passed to
 * pyi_utils_initialize_args(), but may have been modified by subsequent
 * processing code (e.g., Apple event processing).
 *
 * The argv_pyi array is NULL terminated (i.e., contains argc_pyi + 1)
 * entries, and the last entry is NULL).
 *
 * The ownership of array is not transferred, i.e., it should not be
 * explicitly freed by the caller. Instead, the array and its resources
 * are cleaned up oncepyi_utils_free_args() is called.
 */
void pyi_utils_get_args(int *argc, char ***argv)
{
    if (argc) {
        *argc = argc_pyi;
    }
    if (argv) {
        *argv = argv_pyi;
    }
}

/*
 * Free/clean-up the private arguments (pyi_argv).
 */
void pyi_utils_free_args()
{
    /* Free each entry */
    int i;
    for (i = 0; i < argc_pyi; i++) {
        free(argv_pyi[i]);
    }
    /* Free the list */
    free(argv_pyi);
    /* Clean-up the variables, just in case */
    argc_pyi = 0;
    argv_pyi = NULL;
}


/*
 * On Mac OS X this converts events from kAEOpenDocuments and kAEGetURL into sys.argv.
 * After startup, it also forwards kAEOpenDocuments and KAEGetURL events at runtime to the child process.
 *
 * TODO: The below can be simplified considerably if re-written in Objective C (e.g. put into pyi_utils_osx.m).
 */
#if defined(__APPLE__) && defined(WINDOWED)

/* Convert a FourCharCode into a string (useful for debug). Returned buffer is a static buffer, so subsequent calls
 * may overwrite the same buffer. */
static const char *CC2Str(FourCharCode code) {
    /* support up to 3 calls on the same debug print line */
    static char bufs[3][5];
    static unsigned int bufsidx = 0;
    char *buf = bufs[bufsidx++ % 3u];
    snprintf(buf, 5, "%c%c%c%c", (code >> 24) & 0xFF, (code >> 16) & 0xFF, (code >> 8) & 0xFF, code & 0xFF);
    /* buffer is guaranteed to be nul terminated here */
    return buf;
}

/* Generic event forwarder -- forwards an event destined for this process to the child process,
 * copying its param object, if any. Parameter `theAppleEvent` may be NULL, in which case a new
 * event is created with the specified class and id (containing 0 params / no param object). */
static OSErr generic_forward_apple_event(const AppleEvent *const theAppleEvent /* NULL ok */,
                                         const AEEventClass eventClass, const AEEventID evtID,
                                         const char *const descStr)
{
    const FourCharCode evtCode = (FourCharCode)evtID;
    OSErr err;
    AppleEvent childEvent;
    AEAddressDesc target;
    DescType actualType = 0, typeCode = typeWildCard;
    char *buf = NULL; /* dynamic buffer to hold copied event param data */
    Size bufSize = 0, actualSize = 0;

    VS("LOADER [AppleEvent]: Forwarder called for \"%s\".\n", descStr);
    if (!child_pid) {
        /* Child not up yet -- there is no way to "forward" this before child started!. */
         VS("LOADER [AppleEvent]: Child not up yet (child_pid is 0)\n");
         return errAEEventNotHandled;
    }
    VS("LOADER [AppleEvent]: Forwarding '%s' event.\n", CC2Str(evtCode));
    err = AECreateDesc(typeKernelProcessID, &child_pid, sizeof(child_pid), &target);
    if (err != noErr) {
        OTHERERROR("LOADER [AppleEvent]: Failed to create AEAddressDesc: %d\n", (int)err);
        goto out;
    }
    VS("LOADER [AppleEvent]: Created AEAddressDesc.\n");
    err = AECreateAppleEvent(eventClass, evtID, &target, kAutoGenerateReturnID, kAnyTransactionID,
                             &childEvent);
    if (err != noErr) {
        OTHERERROR("LOADER [AppleEvent]: Failed to create event copy: %d\n", (int)err);
        goto release_desc;
    }
    VS("LOADER [AppleEvent]: Created AppleEvent instance for child process.\n");


    if (!theAppleEvent) {
        /* Calling code wants a new event created from scratch, we do so
         * here and it will have 0 params. Assumption: caller knows that
         * the event type in question normally has 0 params. */
        VS("LOADER [AppleEvent]: New AppleEvent class: '%s' code: '%s'\n",
           CC2Str((FourCharCode)eventClass), CC2Str((FourCharCode)evtID));
    } else {
        err = AESizeOfParam(theAppleEvent, keyDirectObject, &typeCode, &bufSize);
        if (err != noErr) {
            /* No params for this event */
            VS("LOADER [AppleEvent]: Failed to get size of param (error=%d) -- event '%s' may lack params.\n",
                (int)err, CC2Str(evtCode));
        } else  {
            /* This event has a param object, copy it. */

            VS("LOADER [AppleEvent]: Got size of param: %ld\n", (long)bufSize);
            buf = malloc(bufSize);
            if (!buf) {
                /* Failed to allocate buffer! */
                OTHERERROR("LOADER [AppleEvent]: Failed to allocate buffer of size %ld: %s\n",
                           (long)bufSize, strerror(errno));
                goto release_evt;
            }
            VS("LOADER [AppleEvent]: Allocated buffer of size: %ld\n", (long)bufSize);
            VS("LOADER [AppleEvent]: Getting param.\n");
            err = AEGetParamPtr(theAppleEvent, keyDirectObject, typeWildCard,
                                &actualType, buf, bufSize, &actualSize);
            if (err != noErr) {
                OTHERERROR("LOADER [AppleEvent]: Failed to get param data.\n");
                goto release_evt;
            }
            if (actualSize > bufSize) {
                /* From reading the Apple API docs, this should never happen, but it pays
                 * to program defensively here. */
                OTHERERROR("LOADER [AppleEvent]: Got param size=%ld > bufSize=%ld, error!\n",
                           (long)actualSize, (long)bufSize);
                goto release_evt;
            }
            VS("LOADER [AppleEvent]: Got param type=%x ('%s') size=%ld\n",
               (UInt32)actualType, CC2Str((FourCharCode)actualType), (long)actualSize);
            VS("LOADER [AppleEvent]: Putting param.\n");
            err = AEPutParamPtr(&childEvent, keyDirectObject, actualType, buf, actualSize);
            if (err != noErr) {
                OTHERERROR("LOADER [AppleEvent]: Failed to put param data.\n");
                goto release_evt;
            }
        }
    }
    VS("LOADER [AppleEvent]: Sending message...\n");
    err = AESendMessage(&childEvent, NULL, kAENoReply, 60 /* 60 = about 1.0 seconds timeout */);
    VS("LOADER [AppleEvent]: Handler sent \"%s\" message to child pid %ld.\n", descStr, (long)child_pid);
release_evt:
    free(buf);
    AEDisposeDesc(&childEvent);
release_desc:
    AEDisposeDesc(&target);
out:
    return err;
}

static Boolean realloc_checked(void **bufptr, Size size)
{
    void *tmp = realloc(*bufptr, size);
    if (!tmp) {
        OTHERERROR("LOADER [AppleEvents]: Failed to allocate a buffer of size %ld.\n", (long)size);
        return false;
    }
    VS("LOADER [AppleEvents]: (re)allocated a buffer of size %ld\n", (long)size);
    *bufptr = tmp;
    return true;
}

/* Handles apple events 'odoc' and 'GURL', both before and after the child_pid is up, Copying them to argv if child
 * not up yet, or otherwise forwarding them to the child if the child is started. */
static OSErr handle_odoc_GURL_events(const AppleEvent *theAppleEvent, const AEEventID evtID)
{
    const FourCharCode evtCode = (FourCharCode)evtID;
    const Boolean apple_event_is_open_doc = evtID == kAEOpenDocuments;
    const char *const descStr = apple_event_is_open_doc ? "OpenDoc" : "GetURL";

    VS("LOADER [AppleEvent]: %s handler called.\n", descStr);

    if (!child_pid) {
        /* Child process is not up yet -- so we pick up kAEOpen and/or kAEGetURL events and append them to argv. */

        AEDescList docList;
        OSErr err;
        long index;
        long count = 0;
        char *buf = NULL; /* Dynamic buffer for URL/file path data -- gets realloc'd as we iterate */

        VS("LOADER [AppleEvent ARGV_EMU]: Processing args for forward...\n");

        err = AEGetParamDesc(theAppleEvent, keyDirectObject, typeAEList, &docList);
        if (err != noErr) return err;

        err = AECountItems(&docList, &count);
        if (err != noErr) return err;

        for (index = 1; index <= count; ++index) /* AppleEvent lists are 1-indexed (I guess because of Pascal?) */
        {
            DescType returnedType;
            AEKeyword keywd;
            Size actualSize = 0, bufSize = 0;
            DescType typeCode = typeWildCard;

            err = AESizeOfNthItem(&docList, index, &typeCode, &bufSize);
            if (err != noErr) {
                OTHERERROR("LOADER [AppleEvent ARGV_EMU]: Failed to get size of Nth item %ld, error: %d\n",
                           index, (int)err);
                continue;
            }

            if (!realloc_checked((void **)&buf, bufSize+1)) {
                /* Not enough memory -- very unlikely but if so keep going */
                OTHERERROR("LOADER [AppleEvent ARGV_EMU]: Not enough memory for Nth item %ld, skipping%d\n", index);
                continue;
            }

            err = AEGetNthPtr(&docList, index, apple_event_is_open_doc ? typeFileURL : typeUTF8Text, &keywd,
                              &returnedType, buf, bufSize, &actualSize);
            if (err != noErr) {
                VS("LOADER [AppleEvent ARGV_EMU]: err[%ld] = %d\n", index-1L, (int)err);
            } else if (actualSize > bufSize) {
                /* This should never happen but is here for thoroughness */
                VS("LOADER [AppleEvent ARGV_EMU]: err[%ld]: not enough space in buffer (%ld > %ld)\n",
                   index-1L, (long)actualSize, (long)bufSize);
            } else {
                /* Copied data to buf, now ensure data is a simple file path and then copy to argv_pyi[argc_pyi] */
                char *tmp_str = NULL;
                Boolean ok;

                buf[actualSize] = 0; /* Ensure NUL-char termination. */
                if (apple_event_is_open_doc) {
                    /* Now, convert file:/// style URLs to an actual filesystem path for argv emu. */
                    CFURLRef url = CFURLCreateWithBytes(NULL, (UInt8 *)buf, actualSize, kCFStringEncodingUTF8,
                                                        NULL);
                    if (url) {
                        CFStringRef path = CFURLCopyFileSystemPath(url, kCFURLPOSIXPathStyle);
                        ok = false;
                        if (path) {
                            const Size newLen = (Size)CFStringGetMaximumSizeOfFileSystemRepresentation(path);
                            if (realloc_checked((void **)&buf, newLen+1)) {
                                bufSize = newLen;
                                ok = CFStringGetFileSystemRepresentation(path, buf, bufSize);
                                buf[bufSize] = 0; /* Ensure NUL termination */
                            }
                            CFRelease(path); /* free */
                        }
                        CFRelease(url); /* free */
                        if (!ok) {
                            VS("LOADER [AppleEvent ARGV_EMU]: "
                               "Failed to convert file:/// path to POSIX filesystem representation for arg %ld!\n",
                               index);
                            continue;
                        }
                    }
                }
                /* Append URL to argv_pyi array, reallocating as necessary */
                VS("LOADER [AppleEvent ARGV_EMU]: arg[%d] = %s\n", (int)argc_pyi, buf);
                tmp_str = strdup(buf);
                ok = realloc_checked((void **)&argv_pyi, (argc_pyi + 2) * sizeof(char *));
                if (!ok || !tmp_str) {
                    /* Out of memory. Extremely unlikely -- not clear what to do here.
                     * Attempt to silently continue. */
                    OTHERERROR("LOADER [AppleEvent ARGV_EMU]: allocation for arg[%d] failed: %s\n",
                               argc_pyi, strerror(errno));
                    free(tmp_str); /* free of possible NULL ok */
                    continue;
                }
                argv_pyi[argc_pyi++] = tmp_str;
                argv_pyi[argc_pyi] = NULL;
                VS("LOADER [AppleEvent ARGV_EMU]: argv entry appended.\n");
            }
        }

        free(buf); /* free of possible-NULL ok */

        err = AEDisposeDesc(&docList);

        return err;
    } /* else ... */

    /* The child process exists.. so we forward events to it */
    return generic_forward_apple_event(theAppleEvent,
                                       apple_event_is_open_doc ? kCoreEventClass : kInternetEventClass,
                                       evtID,
                                       descStr);
}

/* This brings the child_pid's windows to the foreground when the user double-clicks the
 * app's icon again in the macOS UI. 'rapp' is accepted by us only when the child is
 * already running. */
static OSErr handle_rapp_event(const AppleEvent *const theAppleEvent, const AEEventID evtID)
{
    OSErr err;

    VS("LOADER [AppleEvent]: ReopenApp handler called.\n");

    /* First, forward the 'rapp' event to the child */
    err = generic_forward_apple_event(theAppleEvent, kCoreEventClass, evtID, "ReopenApp");

    if (err == noErr) {
        /* Next, create a new activate ('actv') event. We never receive this event because
         * we have no window, but if we did this event would come next. So we synthesize an
         * event that should normally come for a windowed app, so that the child process
         * is brought to the foreground properly. */
        generic_forward_apple_event(NULL /* create new event with 0 params */,
                                    kAEMiscStandards, kAEActivate, "Activate");
    }

    return err;
}

/* Top-level event handler -- dispatches 'odoc', 'GURL', 'rapp', or 'actv' events. */
static pascal OSErr handle_apple_event(const AppleEvent *theAppleEvent, AppleEvent *reply, SRefCon handlerRefCon)
{
    const FourCharCode evtCode = (FourCharCode)handlerRefCon;
    const AEEventID evtID = (AEEventID)handlerRefCon;
    (void)reply; /* unused */

    VS("LOADER [AppleEvent]: %s called with code '%s'.\n", __FUNCTION__, CC2Str(evtCode));

    switch(evtID) {
    case kAEOpenDocuments:
    case kAEGetURL:
        return handle_odoc_GURL_events(theAppleEvent, evtID);
    case kAEReopenApplication:
        return handle_rapp_event(theAppleEvent, evtID);
    case kAEActivate:
        /* This is not normally reached since the bootloader process lacks a window, and it
         * turns out macOS never sends this event to processes lacking a window. However,
         * since the Apple API docs are very sparse, this has been left-in here just in case. */
        return generic_forward_apple_event(theAppleEvent, kAEMiscStandards, evtID, "Activate");
    default:
        /* Not 'GURL', 'odoc', 'rapp', or 'actv'  -- this is not reached unless there is a
         * programming error in the code that sets up the handler(s) in pyi_process_apple_events. */
        OTHERERROR("LOADER [AppleEvent]: %s called with unexpected event type '%s'!\n",
                   __FUNCTION__, CC2Str(evtCode));
        return errAEEventNotHandled;
    }
}

/* This function gets installed as the process-wide UPP event handler.
 * It is responsible for dequeuing events and telling Carbon to forward
 * them to our installed handlers. */
static OSStatus evt_handler_proc(EventHandlerCallRef href, EventRef eref, void *data) {
    VS("LOADER [AppleEvent]: App event handler proc called.\n");
    Boolean release = false;
    EventRecord eventRecord;
    OSStatus err;

    /* Events of type kEventAppleEvent must be removed from the queue
     * before being passed to AEProcessAppleEvent. */
    if (IsEventInQueue(GetMainEventQueue(), eref)) {
        /* RemoveEventFromQueue will release the event, which will
         * destroy it if we don't retain it first. */
        VS("LOADER [AppleEvent]: Event was in queue, will release.\n");
        RetainEvent(eref);
        release = true;
        RemoveEventFromQueue(GetMainEventQueue(), eref);
    }
    /* Convert the event ref to the type AEProcessAppleEvent expects. */
    ConvertEventRefToEventRecord(eref, &eventRecord);
    VS("LOADER [AppleEvent]: what=%hu message=%lx ('%s') modifiers=%hu\n",
       eventRecord.what, eventRecord.message, CC2Str((FourCharCode)eventRecord.message), eventRecord.modifiers);
    /* This will end up calling one of the callback functions
     * that we installed in pyi_process_apple_events() */
    err = AEProcessAppleEvent(&eventRecord);
    if (err == errAEEventNotHandled) {
        VS("LOADER [AppleEvent]: Ignored event.\n");
    } else if (err != noErr) {
        VS("LOADER [AppleEvent]: Error processing event: %d\n", (int)err);
    }
    if (release) {
        ReleaseEvent(eref);
    }
    return noErr;
}

/* Apple event message pump */
void pyi_process_apple_events(bool short_timeout)
{
    static EventHandlerUPP handler;
    static AEEventHandlerUPP handler_ae;
    static Boolean did_install = false;
    static EventHandlerRef handler_ref;
    EventTypeSpec event_types[1];  /*  List of event types to handle. */
    event_types[0].eventClass = kEventClassAppleEvent;
    event_types[0].eventKind = kEventAppleEvent;

    VS("LOADER [AppleEvent]: Processing...\n");

    if (!did_install) {
        OSStatus err;
        handler = NewEventHandlerUPP(evt_handler_proc);
        handler_ae = NewAEEventHandlerUPP(handle_apple_event);
        /* register 'odoc' (open document) */
        err = AEInstallEventHandler(kCoreEventClass, kAEOpenDocuments, handler_ae, (SRefCon)kAEOpenDocuments, false);
        if (err == noErr) {
            /* register 'GURL' (open url) */
            err = AEInstallEventHandler(kInternetEventClass, kAEGetURL, handler_ae, (SRefCon)kAEGetURL, false);
        }
        if (err == noErr) {
            /* register 'rapp' (re-open application) */
            err = AEInstallEventHandler(kCoreEventClass, kAEReopenApplication, handler_ae,
                                        (SRefCon)kAEReopenApplication, false);
        }
        if (err == noErr) {
            /* register 'actv' (activate) */
            err = AEInstallEventHandler(kAEMiscStandards, kAEActivate, handler_ae, (SRefCon)kAEActivate, false);
        }
        if (err == noErr) {
            err = InstallApplicationEventHandler(handler, 1, event_types, NULL, &handler_ref);
        }

        if (err != noErr) {
            /* App-wide handler failed. Uninstall everything. */
            AERemoveEventHandler(kAEMiscStandards, kAEActivate, handler_ae, false);
            AERemoveEventHandler(kCoreEventClass, kAEReopenApplication, handler_ae, false);
            AERemoveEventHandler(kInternetEventClass, kAEGetURL, handler_ae, false);
            AERemoveEventHandler(kCoreEventClass, kAEOpenDocuments, handler_ae, false);
            DisposeEventHandlerUPP(handler);
            DisposeAEEventHandlerUPP(handler_ae);
            VS("LOADER [AppleEvent]: Disposed handlers.\n");
        } else {
            VS("LOADER [AppleEvent]: Installed handlers.\n");
            did_install = true;
        }
    }

    if (did_install) {
        /* Event pump: Process events for up to 1.0 (or 0.25) seconds (or until an error is encountered) */
        const EventTimeout timeout = short_timeout ? 0.25 : 1.0; /* number of seconds */
        for (;;) {
            OSStatus status;
            EventRef event_ref; /* Event that caused ReceiveNextEvent to return. */

            VS("LOADER [AppleEvent]: Calling ReceiveNextEvent\n");

            status = ReceiveNextEvent(1, event_types, timeout, kEventRemoveFromQueue, &event_ref);

            if (status == eventLoopTimedOutErr) {
                VS("LOADER [AppleEvent]: ReceiveNextEvent timed out\n");
                break;
            } else if (status != 0) {
                VS("LOADER [AppleEvent]: ReceiveNextEvent fetching events failed\n");
                break;
            } else {
                /* We actually pulled an event off the queue, so process it.
                   We now 'own' the event_ref and must release it. */
                VS("LOADER [AppleEvent]: ReceiveNextEvent got an EVENT\n");

                VS("LOADER [AppleEvent]: Dispatching event...\n");
                status = SendEventToEventTarget(event_ref, GetEventDispatcherTarget());

                ReleaseEvent(event_ref);
                event_ref = NULL;
                if (status != 0) {
                    VS("LOADER [AppleEvent]: processing events failed\n");
                    break;
                }
            }
        }

        VS("LOADER [AppleEvent]: Out of the event loop.\n");

    } else {
        static Boolean once = false;
        if (!once) {
            /* Log this only once since this is compiled-in even in non-debug mode and we
             * want to avoid console spam, since pyi_process_apple_events may be called a lot. */
            OTHERERROR("LOADER [AppleEvent]: ERROR installing handler.\n");
            once = true;
        }
    }
}
#endif /* if defined(__APPLE__) && defined(WINDOWED) */

#endif /* WIN32 */

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
