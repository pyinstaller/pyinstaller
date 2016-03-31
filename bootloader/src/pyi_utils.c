/*
 * ****************************************************************************
 * Copyright (c) 2013-2016, PyInstaller Development Team.
 * Distributed under the terms of the GNU General Public License with exception
 * for distributing bootloader.
 *
 * The full license is in the file COPYING.txt, distributed with this software.
 * ****************************************************************************
 */

/*
 * Portable wrapper for some utility functions like getenv/setenv,
 * file path manipulation and other shared data types or functions.
 */

/* TODO: use safe string functions */
#define _CRT_SECURE_NO_WARNINGS 1

#ifdef _WIN32
    #include <windows.h>
    #include <direct.h>  /* _mkdir, _rmdir */
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
    #include <limits.h>  /* PATH_MAX */
    #include <signal.h>  /* kill, */
    #include <sys/wait.h>
    #include <unistd.h>  /* rmdir, unlink, mkdtemp */
#endif /* ifdef _WIN32 */
#include <stddef.h> /* ptrdiff_t */
#include <stdio.h>  /* FILE */
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h> /* struct stat */
#include <wchar.h>    /* wchar_t */
#if defined(__APPLE__) && defined(WINDOWED)
    #include <Carbon/Carbon.h>  /* AppleEventsT */
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

/*
 * Watch for OpenDocument AppleEvents and add the files passed in to the
 * sys.argv command line on the Python side.
 *
 * This allows on Mac OS X to open files when a file is dragged and dropped
 * on the App icon in the OS X dock.
 */
#if defined(__APPLE__) && defined(WINDOWED)
static void process_apple_events_new();
#endif

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

    rc = SetEnvironmentVariableW(wvar, wval);
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
    rc = setenv(variable, "");
    #endif /* HAVE_UNSETENV */
#endif     /* _WIN32 */
    return rc;
}

#ifdef _WIN32

/* TODO rename fuction and revisit */
int
pyi_get_temp_path(char *buffer)
{
    int i;
    wchar_t *wchar_ret;
    wchar_t prefix[16];
    wchar_t wchar_buffer[PATH_MAX];

    /*
     * Get path to Windows temporary directory.
     */
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

        if (_wmkdir(wchar_ret) == 0) {
            pyi_win32_utils_to_utf8(buffer, wchar_ret, PATH_MAX);
            free(wchar_ret);
            return 1;
        }
        free(wchar_ret);
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
pyi_get_temp_path(char *buff)
{
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
    if (status->has_temp_directory != true) {
        if (!pyi_get_temp_path(status->temppath)) {
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

    strcpy(fnm, dir);
    dirnmlen = strlen(fnm);

    if (fnm[dirnmlen - 1] != PYI_SEP) {
        strcat(fnm, PYI_SEPSTR);
        dirnmlen++;
    }
    ds = opendir(dir);
    finfo = readdir(ds);

    while (finfo) {
        remove_one(fnm, dirnmlen, finfo->d_name);
        finfo = readdir(ds);
    }
    closedir(ds);
    rmdir(dir);
}
#endif /* ifdef _WIN32 */

/* TODO is this function still used? Could it be removed? */
/*
 * If binaries were extracted, this should be called
 * to remove them
 */
void
cleanUp(ARCHIVE_STATUS *status)
{
    if (status->temppath[0]) {
        pyi_remove_temp_path(status->temppath);
    }
}

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

    strcpy(fnm, path);
    strcpy(name, name_);

    dir = strtok(name, PYI_SEPSTR);

    while (dir != NULL) {
        strcat(fnm, PYI_SEPSTR);
        strcat(fnm, dir);
        dir = strtok(NULL, PYI_SEPSTR);

        if (!dir) {
            break;
        }

#ifdef _WIN32
        pyi_win32_utils_from_utf8(wchar_buffer, fnm, PATH_MAX);

        if (_wstat(wchar_buffer, &sbuf) < 0) {
            _wmkdir(wchar_buffer);
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
    int error = 0;

    if (in == NULL || out == NULL) {
        return -1;
    }

    while (!feof(in)) {
        if (fread(buf, 4096, 1, in) == -1) {
            if (ferror(in)) {
                clearerr(in);
                error = -1;
                break;
            }
        }
        else {
            int rc = fwrite(buf, 4096, 1, out);
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

/* TODO use dlclose() when exiting. */
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
pyi_utils_create_child(const char *thisfile, const int argc, char *const argv[])
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
        FATALERROR("Error creating child process!\n");
        rc = -1;
    }
    return rc;
}

#else /* ifdef _WIN32 */

static int
set_dynamic_library_path(const char* path)
{
    int rc = 0;

    #ifdef AIX
    /* LIBPATH is used to look up dynamic libraries on AIX. */
    pyi_setenv("LIBPATH", path);
    VS("LOADER: LIBPATH=%s\n", path);
    #else
    /* LD_LIBRARY_PATH is used on other *nix platforms (except Darwin). */
    rc = pyi_setenv("LD_LIBRARY_PATH", path);
    VS("LOADER: LD_LIBRARY_PATH=%s\n", path);
    #endif /* AIX */

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
     * and PyQt4 applications.
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

/* Remember child process id. It allows sending a signal to child process.
 * Frozen application always runs in a child process. Parent process is used
 * to setup environment for child process and clean the environment when
 * child exited.
 */
pid_t child_pid = 0;

static void
_signal_handler(int signal)
{
    kill(child_pid, signal);
}

/* Start frozen application in a subprocess. The frozen application runs
 * in a subprocess.
 */
int
pyi_utils_create_child(const char *thisfile, const int argc, char *const argv[])
{
    pid_t pid = 0;
    int rc = 0;
    int i;

    argv_pyi = (char**)calloc(argc + 1, sizeof(char*));
    argc_pyi = 0;

    for (i = 0; i < argc; i++) {
    #if defined(__APPLE__) && defined(WINDOWED)

        /* if we are on a Mac, it passes a strange -psnxxx argument.  Filter it out. */
        if (strstr(argv[i], "-psn") == argv[i]) {
            /* skip */
        }
        else
    #endif
        {
            argv_pyi[argc_pyi++] = strdup(argv[i]);
        }
    }

    #if defined(__APPLE__) && defined(WINDOWED)
    process_apple_events_new();
    #endif

    pid = fork();

    /* Child code. */
    if (pid == 0) {
        /* Replace process by starting a new application. */
        execvp(thisfile, argv_pyi);
    }
    /* Parent code. */
    else {
        child_pid = pid;

        /* Redirect termination signals received by parent to child process. */
        signal(SIGINT, &_signal_handler);
        signal(SIGKILL, &_signal_handler);
        signal(SIGTERM, &_signal_handler);
    }

    wait(&rc);

    /* Parent code. */
    if (child_pid != 0) {
        /* When child process exited, reset signal handlers to default values. */
        signal(SIGINT, SIG_DFL);
        signal(SIGKILL, SIG_DFL);
        signal(SIGTERM, SIG_DFL);

        for (i = 0; i < argc_pyi; i++) {
            free(argv_pyi[i]);
        }
        free(argv_pyi);
    }

    if (WIFEXITED(rc)) {
        return WEXITSTATUS(rc);
    }

    /* Process ended abnormally */
    if (WIFSIGNALED(rc)) {
        /* Mimick the signal the child received */
        raise(WTERMSIG(rc));
    }
    return 1;
}

/*
 * On Mac OS X this converts files from kAEOpenDocuments events into sys.argv.
 */
    #if defined(__APPLE__) && defined(WINDOWED)

/* TODO: Why is this commented out? */
/*
 *  static pascal OSErr handle_open_doc_ae(const AppleEvent *theAppleEvent, AppleEvent *reply, SRefCon handlerRefcon)
 *  {
 *  AEDescList docList;
 *  long index;
 *  long count = 0;
 *  int i;
 *  char *myFileName;
 *  Size actualSize;
 *  DescType returnedType;
 *  AEKeyword keywd;
 *  FSRef theRef;
 *
 *  VS("LOADER: handle_open_doc_ae called.\n");
 *
 *  OSErr err = AEGetParamDesc(theAppleEvent, keyDirectObject, typeAEList, &docList);
 *  if (err != noErr) return err;
 *
 *  err = AECountItems(&docList, &count);
 *  if (err != noErr) return err;
 *  for (index = 1; index <= count; index++)
 *  {
 *    err = AEGetNthPtr(&docList, index, typeFSRef, &keywd, &returnedType, &theRef, sizeof(theRef), &actualSize);
 *
 *    CFURLRef fullURLRef;
 *    fullURLRef = CFURLCreateFromFSRef(NULL, &theRef);
 *    CFStringRef cfString = CFURLCopyFileSystemPath(fullURLRef, kCFURLPOSIXPathStyle);
 *    CFRelease(fullURLRef);
 *    CFMutableStringRef cfMutableString = CFStringCreateMutableCopy(NULL, 0, cfString);
 *    CFRelease(cfString);
 *    CFStringNormalize(cfMutableString, kCFStringNormalizationFormC);
 *    int len = CFStringGetLength(cfMutableString);
 *    const int bufferSize = (len+1)*6;  // in theory up to six bytes per Unicode code point, for UTF-8.
 *    char* buffer = (char*)malloc(bufferSize);
 *    CFStringGetCString(cfMutableString, buffer, bufferSize, kCFStringEncodingUTF8);
 *
 *    argv_pyi = (char**)realloc(argv_pyi,(argc_pyi+2)*sizeof(char*));
 *    argv_pyi[argc_pyi++] = strdup(buffer);
 *    argv_pyi[argc_pyi] = NULL;
 *
 *    free(buffer);
 *  }
 *
 *  err = AEDisposeDesc(&docList);
 *
 *
 *  return (err);
 *  }
 *
 *  static int gQuit = false;
 *
 *  static void apple_main_event_loop()
 *  {
 *  OSErr err;
 *  EventRef eventRef;
 *  EventRecord event;
 *  //UInt32 timeout = 1*60; // number of ticks (1/60th of a second)
 *  VS("LOADER: Entering AppleEvent main loop.\n");
 *
 *  while (!gQuit)
 *  {
 *     // Previous func WaitNextEvent() was deprecated and 32-bit only.
 *     // Func ReceiveNextEvent() is threadsafe and available even for 64-bit OS X.
 *     //gotEvent = WaitNextEvent(highLevelEventMask, &event, timeout, NULL);
 *     err = ReceiveNextEvent(0, NULL, kEventDurationNoWait, true, &eventRef);
 *     if (err == noErr)
 *     {
 *        VS("LOADER: Processing an AppleEvent.\n");
 *        // Convert the event ref to the type AEProcessAppleEvent expects.
 *        ConvertEventRefToEventRecord(eventRef, &event);
 *        AEProcessAppleEvent(&event);
 *        // Func ReceiveNextEvent() requires releasing event manually.
 *        ReleaseEvent(eventRef);
 *     }
 *     gQuit = true;
 *  }
 *  }
 *
 *
 *  static void process_apple_events()
 *  {
 *  OSErr err;
 *
 *  err = AEInstallEventHandler( kCoreEventClass , kAEOpenDocuments , handle_open_doc_ae , 0 , false );
 *  if (err != noErr)
 *   {
 *      VS("LOADER: Error installing AppleEvent handler.\n");
 *   }
 *   else
 *   {
 *      apple_main_event_loop();
 *
 *      err = AERemoveEventHandler(kCoreEventClass, kAEOpenDocuments, handle_open_doc_ae, false);
 *      if (err != noErr)
 *      {
 *         VS("LOADER: Error uninstalling AppleEvent handler.\n");
 *      }
 *   }
 *
 *  }
 */
/*
 * On Mac OS X converts files from kAEOpenDocuments events into sys.argv.
 * New implementation of handling Apple events - works even on 64bit Mac OS X.
 */
static pascal OSStatus
do_filenames_conversion_to_argv(EventHandlerCallRef next_handler,
                                EventRef the_event,
                                void* user_data)
{

/* /////////////// OLD implementation */
/*
 *  AEDescList docList;
 *  long index;
 *  long count = 0;
 *  int i;
 *  char *myFileName;
 *  Size actualSize;
 *  DescType returnedType;
 *  AEKeyword keywd;
 *  FSRef theRef;
 *
 *  VS("LOADER: handle_open_doc_ae called.\n");
 *
 *  OSErr err = AEGetParamDesc(theAppleEvent, keyDirectObject, typeAEList, &docList);
 *  if (err != noErr) return err;
 *
 *  err = AECountItems(&docList, &count);
 *  if (err != noErr) return err;
 *  for (index = 1; index <= count; index++)
 *  {
 *    err = AEGetNthPtr(&docList, index, typeFSRef, &keywd, &returnedType, &theRef, sizeof(theRef), &actualSize);
 *
 *    CFURLRef fullURLRef;
 *    fullURLRef = CFURLCreateFromFSRef(NULL, &theRef);
 *    CFStringRef cfString = CFURLCopyFileSystemPath(fullURLRef, kCFURLPOSIXPathStyle);
 *    CFRelease(fullURLRef);
 *    CFMutableStringRef cfMutableString = CFStringCreateMutableCopy(NULL, 0, cfString);
 *    CFRelease(cfString);
 *    CFStringNormalize(cfMutableString, kCFStringNormalizationFormC);
 *    int len = CFStringGetLength(cfMutableString);
 *    const int bufferSize = (len+1)*6;  // in theory up to six bytes per Unicode code point, for UTF-8.
 *    char* buffer = (char*)malloc(bufferSize);
 *    CFStringGetCString(cfMutableString, buffer, bufferSize, kCFStringEncodingUTF8);
 *
 *    argv_pyi = (char**)realloc(argv_pyi,(argc_pyi+2)*sizeof(char*));
 *    argv_pyi[argc_pyi++] = strdup(buffer);
 *    argv_pyi[argc_pyi] = NULL;
 *
 *    free(buffer);
 *  }
 *
 *  err = AEDisposeDesc(&docList);
 */
/* //////////////////////////////////////////// */

    /* Handle the kAEOpenDocuments event. */
    VS("LOADER: AppleEvent - do_filenames_coversion_to_argv called.\n");
    /* Obtain filenames from event. */
    /* Every event type contains different additional information. */
    /* TODO */
    /* GetEventParameter(the_event, ) */
    /* TODO */
    /* Report success. */
    return noErr;
}

/* TODO Unfinished, issue #1309. */
static void
process_apple_events_new()
{
    OSStatus handler_install_status;
    OSStatus handler_remove_status;
    OSStatus event_received;
    EventTypeSpec event_types[1];  /*  List of event types to handle. */
    EventHandlerUPP handler_open_doc;
    EventHandlerRef handler_ref; /* Reference for later removing the event handler. */
    EventRef event_ref;          /* Event that caused ReceiveNextEvent to return. */
    OSType ev_class;
    UInt32 ev_kind;
    EventTimeout timeout = 3.0;  /* number of ticks (1/60th of a second) */

    VS("LOADER: AppleEvent - processing...\n");
    /* Event types we are interested in. */
    event_types[0].eventClass = kCoreEventClass;
    event_types[0].eventKind = kAEOpenDocuments;
    /* Carbon Event Manager requires convert the function pointer to type EventHandlerUPP. */
    /* https://developer.apple.com/legacy/library/documentation/Carbon/Conceptual/Carbon_Event_Manager/Tasks/CarbonEventsTasks.html */
    handler_open_doc = NewEventHandlerUPP(do_filenames_conversion_to_argv);
    /* Install the event handler. */
    /* InstallApplicationEventHandler is a macro for 'InstallEventHandler' where the event target */
    /* is Application. */
    /* We do not have any windows so having Application as event target should be fine. */
    handler_install_status = InstallApplicationEventHandler(handler_open_doc, 1,
                                                            event_types, NULL,
                                                            &handler_ref);

    if (handler_install_status == noErr) {
        VS("LOADER: AppleEvent - installed handler.\n");

        /* TODO */
        /* ReceiveNextEvent(); */
        /* RunCurrentEventLoop(timeout); */
        /* RunApplicationEventLoop(); */

        /* Previous func WaitNextEvent() was deprecated and 32-bit only. */
        /* Func ReceiveNextEvent() is threadsafe and available even for 64-bit OS X. */
        /* gotEvent = WaitNextEvent(highLevelEventMask, &event, timeout, NULL); */
        /* event_received = ReceiveNextEvent(1, event_types, kEventDurationForever, true, &event_ref); */
        /* event_received = ReceiveNextEvent(0, NULL, kEventDurationNoWait, true, &event_ref); */
        /* TODO */
        /* handler_remove_status = RemoveEventHandler(handler_ref); */
        /*
         *  if (event_received == noErr)
         *  {
         *   VS("LOADER: AppleEvent - received event.\n");
         *   ev_class = GetEventClass(event_ref);
         *   ev_kind = GetEventKind(event_ref);
         *   VS("LOADER: AppleEvent - event type: %u\n", ev_kind);
         *   //if (GetEventKind(event_ref) == kAEOpenDocuments)
         *   if (ev_class == kCoreEventClass)
         *   {
         *       VS("LOADER: AppleEvent - right class.\n");
         *   }
         *
         *   ReleaseEvent(event_ref);
         *  }
         *  else
         *  {
         *   VS("LOADER: AppleEvent - ERROR receiving events code: %d\n", event_received);
         *  }*/

    }
    else {
        VS("LOADER: AppleEvent - ERROR installing handler.\n");
    }

    /* Remove handler_ref reference when we are done with EventHandlerUPP. */
    /* Carbon Event Manager does not do this automatically. */
    DisposeEventHandlerUPP(handler_open_doc)
}
    #endif /* if defined(__APPLE__) && defined(WINDOWED) */

#endif  /* WIN32 */
