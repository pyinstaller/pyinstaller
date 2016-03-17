/*
 * ****************************************************************************
 * Copyright (c) 2013-2016, PyInstaller Development Team.
 * Distributed under the terms of the GNU General Public License with exception
 * for distributing bootloader.
 *
 * The full license is in the file COPYING.txt, distributed with this software.
 * ****************************************************************************
 */

/* TODO move this code to file  pyi_win32.c. */

/*
 * Functions in this file are windows specific and are mostly related to handle
 * Side-by-Side assembly:
 *
 * https://en.wikipedia.org/wiki/Side-by-side_assembly
 */

#ifdef _WIN32

/* windows.h will use API for WinServer 2003 with SP1 and WinXP with SP2 */
#define _WIN32_WINNT 0x0502

/* TODO: use safe string functions */
#define _CRT_SECURE_NO_WARNINGS 1

#include <windows.h>
#include <commctrl.h> /* InitCommonControls */
#include <stdio.h>    /* _fileno */
#include <io.h>       /* _get_osfhandle */
#include <signal.h>   /* signal */

/* PyInstaller headers. */
#include "msvc_stdint.h" /* int32_t */
#include "pyi_global.h"  /* PATH_MAX */
#include "pyi_archive.h"
#include "pyi_path.h"
#include "pyi_utils.h"
#include "pyi_win32_utils.h"

static HANDLE hCtx = INVALID_HANDLE_VALUE;
static ULONG_PTR actToken;

#ifndef STATUS_SXS_EARLY_DEACTIVATION
    #define STATUS_SXS_EARLY_DEACTIVATION 0xC015000F
#endif

char *
GetWinErrorString()
{
    DWORD error_code = GetLastError();
    char * errorString = NULL;

    FormatMessageA(FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM, /* dwFlags */
                   NULL,                                                        /* lpSource */
                   error_code,                                                  /* dwMessageID, */
                   0,                                                           /* dwLanguageID, */
                   (char *)(&errorString),                                      /* lpBuffer; see FORMAT_MESSAGE_ALLOCATE_BUFFER */
                   0,                                                           /* nSize */
                   NULL                                                         /* Arguments */
                   );

    if (NULL == errorString) {
        return "FormatMessage failed.";
    }
    return errorString;

}

int
CreateActContext(const char *manifestpath)
{
    wchar_t * manifestpath_w;
    ACTCTXW ctx;
    BOOL activated;
    HANDLE k32;

    HANDLE (WINAPI * CreateActCtx)(PACTCTXW pActCtx);
    BOOL (WINAPI * ActivateActCtx)(HANDLE hActCtx, ULONG_PTR * lpCookie);

    /* Setup activation context */
    VS("LOADER: manifestpath: %s\n", manifestpath);
    manifestpath_w = pyi_win32_utils_from_utf8(NULL, manifestpath, 0);

    k32 = LoadLibraryA("kernel32");
    CreateActCtx = (void*)GetProcAddress(k32, "CreateActCtxW");
    ActivateActCtx = (void*)GetProcAddress(k32, "ActivateActCtx");

    if (!CreateActCtx || !ActivateActCtx) {
        VS("LOADER: Cannot find CreateActCtx/ActivateActCtx exports in kernel32.dll\n");
        return 0;
    }

    ZeroMemory(&ctx, sizeof(ctx));
    ctx.cbSize = sizeof(ACTCTX);
    ctx.lpSource = manifestpath_w;
    ctx.dwFlags = ACTCTX_FLAG_SET_PROCESS_DEFAULT;

    hCtx = CreateActCtx(&ctx);
    free(manifestpath_w);

    if (hCtx != INVALID_HANDLE_VALUE) {
        VS("LOADER: Activation context created\n");
        activated = ActivateActCtx(hCtx, &actToken);

        if (activated) {
            VS("LOADER: Activation context activated\n");
            return 1;
        }
    }

    hCtx = INVALID_HANDLE_VALUE;
    VS("LOADER: Error activating the context: ActivateActCtx: \n%s\n",
       GetWinErrorString());
    return 0;
}

/* Convert a wide string to an ANSI string.
 *
 *  Returns a newly allocated buffer containing the ANSI characters terminated by a null
 *  character. The caller is responsible for freeing this buffer with free().
 *
 *  Returns NULL and logs error reason if encoding fails.
 */

char *
pyi_win32_wcs_to_mbs(const wchar_t *wstr)
{
    DWORD len, ret;
    char * str;

    /* NOTE: setlocale hysterics are not needed on Windows - this function
     *  has an explicit codepage parameter. CP_ACP means "current ANSI codepage"
     *  which is set in the "Language for Non-Unicode Programs" control panel setting. */

    /* Get buffer size by passing NULL and 0 for output arguments */
    len = WideCharToMultiByte(CP_ACP,  /* CodePage */
                              0,       /* dwFlags */
                              wstr,    /* lpWideCharStr */
                              -1,      /* cchWideChar - length in chars */
                              NULL,    /* lpMultiByteStr */
                              0,       /* cbMultiByte - length in bytes */
                              NULL,    /* lpDefaultChar */
                              NULL     /* lpUsedDefaultChar */
                              );

    if (0 == len) {
        FATALERROR("Failed to get ANSI buffer size"
                   "(WideCharToMultiByte: %s)\n",
                   GetWinErrorString()
                   );
        return NULL;
    }

    str = (char *)calloc(len + 1, sizeof(char));

    ret = WideCharToMultiByte(CP_ACP,    /* CodePage */
                              0,         /* dwFlags */
                              wstr,      /* lpWideCharStr */
                              -1,        /* cchWideChar - length in chars */
                              str,       /* lpMultiByteStr */
                              len,       /* cbMultiByte - length in bytes */
                              NULL,      /* lpDefaultChar */
                              NULL       /* lpUsedDefaultChar */
                              );

    if (0 == ret) {
        FATALERROR("Failed to encode filename as ANSI"
                   "(WideCharToMultiByte: %s)\n",
                   GetWinErrorString()
                   );
        return NULL;
    }
    return str;
}

/* Convert a wide string to an ANSI string, also attempting to get the MS-DOS
 *  ShortFileName if the string is a filename. ShortFileName allows Python 2.7 to
 *  accept filenames which cannot encode in the current ANSI codepage.
 *
 *  Returns a newly allocated buffer containing the ANSI characters terminated by a null
 *  character. The caller is responsible for freeing this buffer with free().
 *
 *  Returns NULL and logs error reason if encoding fails.
 */

char *
pyi_win32_wcs_to_mbs_sfn(const wchar_t *wstr)
{
    DWORD wsfnlen;
    wchar_t * wstr_sfn = NULL;
    char * str = NULL;
    DWORD ret;

    wsfnlen = GetShortPathNameW(wstr, NULL, 0);

    if (wsfnlen) {
        wstr_sfn = (wchar_t *)calloc(wsfnlen + 1, sizeof(wchar_t));
        ret = GetShortPathNameW(wstr, wstr_sfn, wsfnlen);

        if (ret) {
            str = pyi_win32_wcs_to_mbs(wstr_sfn);
        }
        free(wstr_sfn);
    }

    if (!str) {
        VS("Failed to get short path name for filename. GetShortPathNameW: \n%s\n",
           GetWinErrorString()
           );
        str = pyi_win32_wcs_to_mbs(wstr);
    }
    return str;
}

/* Convert a UTF-8 string to an ANSI string, also attempting to get the MS-DOS
 *  ShortFileName if the string is a filename. ShortFileName allows Python 2.7 to
 *  accept filenames which cannot encode in the current ANSI codepage.
 *
 *  Preserves the filename's original basename, since the bootloader code depends on
 *  the unmodified basename. Assumes that the basename can be encoded using the current
 *  ANSI codepage.
 *
 *  This is a workaround for <https://github.com/pyinstaller/pyinstaller/issues/298>.
 *
 *  Copies the converted string to `dest`, which must be a buffer
 *  of at least PATH_MAX characters. Returns 'dest' if successful.
 *
 *  Returns NULL and logs error reason if encoding fails.
 */
char *
pyi_win32_utf8_to_mbs_sfn_keep_basename(char * dest, const char * src)
{
    char * mbs_buffer;
    char * mbs_sfn_buffer;
    char basename[PATH_MAX];
    char dirname[PATH_MAX];

    /* Convert path to mbs*/
    mbs_buffer = pyi_win32_utf8_to_mbs(NULL, src, 0);

    if (NULL == mbs_buffer) {
        return NULL;
    }

    /* Convert path again to mbs, this time with SFN */
    mbs_sfn_buffer = pyi_win32_utf8_to_mbs_sfn(NULL, src, 0);

    if (NULL == mbs_sfn_buffer) {
        free(mbs_buffer);
        return NULL;
    }

    pyi_path_basename(basename, mbs_buffer);
    pyi_path_dirname(dirname, mbs_sfn_buffer);
    pyi_path_join(dest, dirname, basename);
    free(mbs_buffer);
    free(mbs_sfn_buffer);
    return dest;
}

/* We shouldn't need to convert ANSI to wchar_t since everything is provided as wchar_t */

/* The following are used to convert the UTF-16 strings provided by Windows
 * into UTF-8 so we can store them in the `char *` variables and fields
 * we use on Linux. Storing them like this is a wart, but storing them as `wchar_t *`
 * and converting back and forth everywhere on Linux/OS X is an even bigger wart
 */

/* Convert elements of wargv to UTF-8 */

char **
pyi_win32_argv_to_utf8(int argc, wchar_t **wargv)
{
    int i, j;
    char ** argv;

    argv = (char **)calloc(argc + 1, sizeof(char *));

    for (i = 0; i < argc; i++) {
        argv[i] = pyi_win32_utils_to_utf8(NULL, wargv[i], 0);

        if (NULL == argv[i]) {
            goto err;
        }
    }
    argv[argc] = NULL;

    return argv;
err:

    for (j = 0; j <= i; j++) {
        free(argv[j]);
    }
    free(argv);
    return NULL;
}

/* Convert elements of wargv back from UTF-8. Used when calling
 *  PySys_SetArgv on Python 3.
 */

wchar_t **
pyi_win32_wargv_from_utf8(int argc, char **argv)
{
    int i, j;
    wchar_t ** wargv;

    wargv = (wchar_t **)calloc(argc + 1, sizeof(wchar_t *));

    for (i = 0; i < argc; i++) {
        wargv[i] = pyi_win32_utils_from_utf8(NULL, argv[i], 0);

        if (NULL == wargv[i]) {
            goto err;
        }
    }
    wargv[argc] = NULL;

    return wargv;
err:

    for (j = 0; j <= i; j++) {
        free(wargv[j]);
    }
    free(wargv);
    return NULL;
}

/*
 * Encode wchar_t (UTF16) into char (UTF8).
 *
 * `wstr` must be null-terminated.
 *
 * If `str` is not NULL, copies the result into the given buffer, which must hold
 * at least `len` bytes. Returns the given buffer if successful. Returns NULL on
 * encoding failure, or if the UTF-8 encoding requires more than `len` bytes.
 *
 * If `str` is NULL, allocates and returns a new buffer to store the result. The
 * `len` argument is ignored. Returns NULL on encoding failure. The caller is
 * responsible for freeing the returned buffer using free().
 *
 */
char *
pyi_win32_utils_to_utf8(char *str, const wchar_t *wstr, size_t len)
{
    char * output;

    if (NULL == str) {
        /* Get buffer size by passing NULL and 0 for output arguments
         * -1 for cchWideChar means string is null-terminated
         */
        len = WideCharToMultiByte(CP_UTF8,              /* CodePage */
                                  0,                    /* dwFlags */
                                  wstr,                 /* lpWideCharStr */
                                  -1,                   /* cchWideChar - length in chars */
                                  NULL,                 /* lpMultiByteStr */
                                  0,                    /* cbMultiByte - length in bytes */
                                  NULL,                 /* lpDefaultChar */
                                  NULL                  /* lpUsedDefaultChar */
                                  );

        if (0 == len) {
            FATALERROR("Failed to get UTF-8 buffer size (WideCharToMultiByte: %s)\n",
                       GetWinErrorString()
                       );
            return NULL;
        }

        output = (char *)calloc(len + 1, sizeof(char));
    }
    else {
        output = str;
    }

    len = WideCharToMultiByte(CP_UTF8,              /* CodePage */
                              0,                    /* dwFlags */
                              wstr,                 /* lpWideCharStr */
                              -1,                   /* cchWideChar - length in chars */
                              output,               /* lpMultiByteStr */
                              (DWORD)len,           /* cbMultiByte - length in bytes */
                              NULL,                 /* lpDefaultChar */
                              NULL                  /* lpUsedDefaultChar */
                              );

    if (len == 0) {
        FATALERROR("Failed to encode wchar_t as UTF-8 (WideCharToMultiByte: %s)\n",
                   GetWinErrorString()
                   );
        return NULL;
    }
    return output;
}

/*
 * Decode char (UTF8) into wchar_t (UTF16).
 *
 * `str` must be null-terminated.
 *
 * If `wstr` is not NULL, copies the result into the given buffer, which must hold
 * at least `wlen` characters. Returns the given buffer if successful. Returns NULL on
 * encoding failure, or if the UTF-16 encoding requires more than `wlen` characters.
 *
 * If `wstr` is NULL, allocates and returns a new buffer to store the result. The
 * `wlen` argument is ignored. Returns NULL on encoding failure. The caller is
 * responsible for freeing the returned buffer using free().
 */

wchar_t *
pyi_win32_utils_from_utf8(wchar_t *wstr, const char *str, size_t wlen)
{
    wchar_t * output;

    if (NULL == wstr) {
        /* Get buffer size by passing NULL and 0 for output arguments
         * -1 for cbMultiByte means string is null-terminated.
         */
        wlen = MultiByteToWideChar(CP_UTF8,             /* CodePage */
                                   0,                   /* dwFlags */
                                   str,                 /* lpMultiByteStr */
                                   -1,                  /* cbMultiByte - length in bytes */
                                   NULL,                /* lpWideCharStr */
                                   0                    /* cchWideChar - length in chars */
                                   );

        if (0 == wlen) {
            FATALERROR("Failed to get UTF-8 buffer size (WideCharToMultiByte: %s)\n",
                       GetWinErrorString()
                       );
            return NULL;
        }

        output = (wchar_t *)calloc(wlen + 1, sizeof(wchar_t));
    }
    else {
        output = wstr;
    }

    wlen = MultiByteToWideChar(CP_UTF8,              /* CodePage */
                               0,                    /* dwFlags */
                               str,                  /* lpMultiByteStr */
                               -1,                   /* cbMultiByte - length in bytes */
                               output,               /* lpWideCharStr */
                               (DWORD)wlen           /* cchWideChar - length in chars */
                               );

    if (wlen == 0) {
        FATALERROR("Failed to encode wchar_t as UTF-8 (WideCharToMultiByte: %s)\n",
                   GetWinErrorString()
                   );
        return NULL;
    }
    return output;
}

/* Convenience function to convert UTF-8 to ANSI optionally with SFN.
 * Calls pyi_win32_utils_from_utf8 followed by pyi_win32_wcs_to_mbs_sfn
 */

char *
pyi_win32_utf8_to_mbs_ex(char * dst, const char * src, size_t max, int sfn)
{
    wchar_t * wsrc;
    char * mbs;

    wsrc = pyi_win32_utils_from_utf8(NULL, src, 0);

    if (NULL == wsrc) {
        return NULL;
    }

    if (sfn) {
        mbs = pyi_win32_wcs_to_mbs_sfn(wsrc);
    }
    else {
        mbs = pyi_win32_wcs_to_mbs(wsrc);
    }

    free(wsrc);

    if (NULL == mbs) {
        return NULL;
    }

    if (dst) {
        strncpy(dst, mbs, max);
        free(mbs);
        return dst;
    }
    else {
        return mbs;
    }
}

char *
pyi_win32_utf8_to_mbs(char * dst, const char * src, size_t max)
{
    return pyi_win32_utf8_to_mbs_ex(dst, src, max, 0);
}

char *
pyi_win32_utf8_to_mbs_sfn(char * dst, const char * src, size_t max)
{
    return pyi_win32_utf8_to_mbs_ex(dst, src, max, 1);
}
/* Convenience function to convert UTF-8 argv to ANSI characters for Py2Sys_SetArgv
 *  Optionally use ShortFileNames to improve compatibility on Python 2.
 *
 *  Returns a newly allocated array of pointers to newly allocated buffers containing
 *  ANSI characters. The caller is responsible for freeing both the array and the buffers
 *  using free()
 *
 *  Returns NULL and logs the error reason if an error occurs.
 */

char **
pyi_win32_argv_mbcs_from_utf8_ex(int argc, char **argv, int sfn)
{
    int i, j;
    char ** argv_mbcs;

    argv_mbcs = (char **)calloc(argc + 1, sizeof(char *));

    for (i = 0; i < argc; i++) {
        argv_mbcs[i] = pyi_win32_utf8_to_mbs_ex(NULL, argv[i], 0, sfn);

        if (NULL == argv_mbcs[i]) {
            goto err;
        }
    }
    argv_mbcs[argc] = NULL;

    return argv_mbcs;
err:

    for (j = 0; j <= i; j++) {
        free(argv_mbcs[j]);
    }
    free(argv_mbcs);
    return NULL;
}

/* Convert elements of __wargv to ANSI characters.
 *  See pyi_win32_argv_mbcs_from_utf8_ex
 */
char **
pyi_win32_argv_mbcs_from_utf8(int argc, char **argv)
{
    return pyi_win32_argv_mbcs_from_utf8_ex(argc, argv, 0);
}

/* Convert elements of __wargv to ANSI encoded MS-DOS ShortFileNames.
 *  See pyi_win32_argv_mbcs_from_utf8_ex
 */
char **
pyi_win32_argv_mbcs_from_utf8_sfn(int argc, char **argv)
{
    return pyi_win32_argv_mbcs_from_utf8_ex(argc, argv, 1);
}

#endif  /* _WIN32 */
