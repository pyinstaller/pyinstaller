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

#ifndef PYI_MAIN_H
#define PYI_MAIN_H


#include "pyi_global.h"


typedef struct _archive ARCHIVE;
typedef struct _splash_context SPLASH_CONTEXT;


/* Console hiding/minimization options. Windows only. */
#if defined(_WIN32) && !defined(WINDOWED)

/* bootloader option strings */
#define HIDE_CONSOLE_OPTION_HIDE_EARLY "hide-early"
#define HIDE_CONSOLE_OPTION_HIDE_LATE "hide-late"
#define HIDE_CONSOLE_OPTION_MINIMIZE_EARLY "minimize-early"
#define HIDE_CONSOLE_OPTION_MINIMIZE_LATE "minimize-late"

/* values used in PYI_CONTEXT field */
enum PYI_HIDE_CONSOLE
{
    PYI_HIDE_CONSOLE_UNUSED = 0,
    PYI_HIDE_CONSOLE_HIDE_EARLY = 1,
    PYI_HIDE_CONSOLE_HIDE_LATE = 2,
    PYI_HIDE_CONSOLE_MINIMIZE_EARLY = 3,
    PYI_HIDE_CONSOLE_MINIMIZE_LATE = 4
};

#endif


typedef struct
{
    /* Command line arguments passed to the application */
    int argc;
    char **argv;

    /* A copy of command-line arguments, so that PyInstaller can manipulate
     * them if necessary.
     *
     * For example, in macOS .app bundles, we need to remove the `-psnxxx`
     * argument. Furthermore, if argv-emulation is enabled for macOS .app
     * bundles, we receive AppleEvents and convert them to command-line
     * arguments.
     *
     * In addition, the `pyi_argv` array itself is NULL-terminated (in
     * contrast to the original `argv` array, it has `pyi_argc + 1`
     * elements, and `pyi_argv[pyi_argc]` is NULL). This makes it
     * suitable for passing to `execvp` calls that are used on POSIX to
     * spawn onefile child process and also used on POSIX systems other
     * than macOS for onedir process to restart itself.
     *
     * These fields are initialized on on-demand basis, in the codepaths
     * that involve `execvp` calls and/or macOS app bundles. Look for
     * `pyi_utils_initialize_args` calls.
     *
     * While setting up the embedded python interpreter configuration,
     * the corresponding codepath automatically chooses between argc/argv
     * and pyi_argc/pyi_argv depending on the availability of the latter.
     * This means that if `pyi_utils_initialize_args` was called at
     * some point before, the modified arguments are passed on to the
     * python interpreter (and will appear in sys.argv). */
    int pyi_argc;
    char **pyi_argv;

    /* Fully resolved path to the executable */
    char executable_filename[PATH_MAX];

    /* Fully resolved path to the main PKG archive */
    char archive_filename[PATH_MAX];

    /* Main PKG archive */
    ARCHIVE *archive;

    /* Splash screen context structure */
    SPLASH_CONTEXT *splash;

    /* Flag indicating whether the application's main PKG archive has
     * onefile semantics or not (i.e., needs to extract files to
     * temporary directory and run a child process). In addition to
     * onefile applications themselves, this also applies to applications
     * that used MERGE() for multi-package. */
    unsigned char is_onefile;

    /* Flag indicating whether the process needs to extract files
     * to temporary directory. In application with onefile semantics
     * (`is_onefile = 1`), this flag should be set to 1 in the parent
     * process and to 0 in the child process. In application without
     * onefile semantics, it should always be 0. */
    unsigned char needs_to_extract;

    /* Application's top-level directory (sys._MEIPASS), where the data
     * and shared libraries are. For applications with onefile semantics,
     * this is ephemeral temporary directory where application unpacked
     * itself. */
    char application_home_dir[PATH_MAX];

    /* Handle to loaded python shared library. */
    dylib_t python_dll;

    /* Flag indicating whether symbols from Python shared library have
     * been successfully loaded. Used to gracefully handle cleanup in
     * situations when Python shared library is successfully loaded,
     * but we fail to import the symbols. */
    unsigned char python_symbols_loaded;

    /* Strict unpack mode for onefile builds. This flag is dynamically
     * controlled by `PYINSTALLER_STRICT_UNPACK_MODE` environment variable
     * (enabled by a value different from 0). If enabled, extraction of
     * onefile builds (either splash screen dependencies, or main archive
     * unpacking) fails if trying to overwrite an existing file. Otherwise,
     * a warning is displayed on stderr. This is primarily used for
     * run-time detection of duplicated resources in onefile archives on
     * PyInstaller's CI. */
    unsigned char strict_unpack_mode;

#if defined(_WIN32)
    /* Security descriptor that limits the access to created directory
     * to the user. Used with `pyi_win32_mkdir`, when creating the
     * application's temporary top-level directory and its sub-directories
     * in onefile mode.
     *
     * Must be explicitly initialized by calling
     * `pyi_win32_initialize_security_descriptor`, and freed by calling
     * `pyi_win32_free_security_descriptor`.
     */
    PSECURITY_DESCRIPTOR security_descriptor;
#endif

    /**
     * Runtime options
     */

    /* Run-time temporary directory path in onefile builds. If this
     * option is not specified, the OS-configured temporary directory
     * is used.
     *
     * NOTE: if non-NULL, the pointer points at the TOC buffer entry in
     * the `archive` structure! */
    const char *runtime_tmpdir;

    /* Contents sub-directory in onedir builds.
     *
     * NOTE: if non-NULL, the pointer points at the TOC buffer entry in
     * the `archive` structure! */
    const char *contents_subdirectory;

    /* Console hiding/minimization options for Windows console builds. */
#if defined(_WIN32) && !defined(WINDOWED)
    unsigned char hide_console;
#endif

    /* Disable traceback in the unhandled exception message in
     * windowed/noconsole builds (unhandled exception dialog in
     * Windows noconsole builds, syslog message in macOS .app
     * bundles) */
#if defined(WINDOWED)
    unsigned char disable_windowed_traceback;
#endif

    /* Argv emulation for macOS .app bundles */
#if defined(__APPLE__) && defined(WINDOWED)
    unsigned char macos_argv_emulation;
#endif

    /* Ignore signals passed to parent process of a onefile application
     * (POSIX systems only).
     *
     * If this option is not specified, a custom sugnal handler is
     * installed that forwards signals to the child process.
     *
     * If this option is specified, a custom no-op signal handler is
     * installed, so signals are effectively ignored.
     *
     * In current implementation, SIGCHLD, SIGCLD, and SIGTSTP are exempt
     * from modification, and use *default* signal handler regardless of
     * whether this option is specified or not. */
#if !defined(_WIN32)
    unsigned char ignore_signals;
#endif
} PYI_CONTEXT;

extern PYI_CONTEXT *global_pyi_ctx;


int pyi_main(PYI_CONTEXT *pyi_ctx);


#endif /* PYI_MAIN_H */
