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

/* This file contains three different entry points, for different
 * combinations of OS and pre-processor definitions:
 *   - wWinMain: for Windows with console=False
 *   - wmain: for Windows with console=True
 *   - main: for POSIX systems
 */

#ifdef _WIN32
    #include <windows.h>
    #include <wchar.h>
#endif

#include <stdlib.h>
#include <stdio.h>
#include <string.h>

#ifdef __FreeBSD__
    #include <floatingpoint.h>
#endif

#include "pyi_main.h"
#include "pyi_global.h"
#include "pyi_win32_utils.h"


/* Global PYI_CONTEXT structure used for bookkeeping of state variables.
 * Since the structure is always used, we can define as static here.
 *
 * We also define a pointer to it, which is intended for use in callbacks
 * and signal handlers that do not allow passing additional data. In
 * accordance with encapsulation principle, it is preferred that the
 * pointer to structure is passed along regular function calls.
 *
 * NOTE: per C standard, static objects are default-initialized, so
 * we do not need explicit zero-initialization.
 */
static PYI_CONTEXT _pyi_ctx;

PYI_CONTEXT *global_pyi_ctx = NULL;


#if defined(_WIN32)

/* Prevent programs compiled with MinGW (gcc) from performing glob-style
 * wildcard expansion of command-line arguments. This keeps behavior
 * consistent between applications that use MinGW-compiled and MSVC-compiled
 * bootloader. */
extern int _CRT_glob = 0;

#if defined(WINDOWED)

/* Entry point for Windows when console=False */
int WINAPI
wWinMain(
    HINSTANCE hInstance,      /* handle to current instance */
    HINSTANCE hPrevInstance,  /* handle to previous instance */
    LPWSTR lpCmdLine,         /* pointer to command line */
    int nCmdShow              /* show state of window */
    )
{
    /* Convert wide-char arguments to UTF-8 and store them in global
     * context structure */
    _pyi_ctx.argc = __argc;
    _pyi_ctx.argv = pyi_win32_argv_to_utf8(__argc, __wargv);

    global_pyi_ctx = &_pyi_ctx;

    return pyi_main(global_pyi_ctx);
}

#else /* defined(WINDOWED) */

/* Entry point for Windows when console=True */
int
wmain(int argc, wchar_t **argv)
{
    /* Convert wide-char arguments to UTF-8 and store them in global
     * context structure */
    _pyi_ctx.argc = argc;
    _pyi_ctx.argv = pyi_win32_argv_to_utf8(argc, argv);

    global_pyi_ctx = &_pyi_ctx;

    return pyi_main(global_pyi_ctx);
}

#endif /* defined(WINDOWED) */

#else /* defined(_WIN32) */

/* Entry point for POSIX */
int
main(int argc, char **argv)
{
#ifdef __FreeBSD__
    /* PEP-754 requires that FP exceptions run in "no stop" mode by default,
     * and until C vendors implement C99's ways to control FP exceptions,
     * Python requires non-stop mode.  Alas, some platforms enable FP
     * exceptions by default. Here we disable them. */
    fpsetmask(fpgetmask() & ~FP_X_OFL);
#endif

    /* Store arguments in global context structure */
    _pyi_ctx.argc = argc;
    _pyi_ctx.argv = argv;

    global_pyi_ctx = &_pyi_ctx;

    return pyi_main(global_pyi_ctx);
}

#endif /* defined(WIN32) */
