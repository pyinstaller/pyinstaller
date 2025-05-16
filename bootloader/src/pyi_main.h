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

#ifndef _WIN32
    #include <sys/types.h> /* pid_t */
#endif


struct ARCHIVE;
struct SPLASH_CONTEXT;
struct DYLIB_PYTHON;

#if defined(__APPLE__) && defined(WINDOWED)
struct APPLE_EVENT_HANDLER_CONTEXT;
#endif


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


/* Process levels */
enum PYI_PROCESS_LEVEL
{
    /* Used to designate *parent* process level for top-level / entry-point
     * processes. */
    PYI_PROCESS_LEVEL_UNKNOWN = -2,
    /* Main application process of onedir application process on POSIX
     * systems where we modify library search path via environment variable;
     * such process needs to restart itself for changes to take effect.
     * Also used on said POSIX systems to designate parent / launcher
     * process in onefile applications with splash screen enabled, which
     * similarly needs to restart itself for changes in library search
     * path to take effect before bundled Tcl/Tk shared libraries (and
     * their bundled dependencies) are loaded for splash screen. */
    PYI_PROCESS_LEVEL_PARENT_NEEDS_RESTART = -1,
    /* Parent / launcher process in onefile applications; unpacks the
     * application, and starts the main application process. */
    PYI_PROCESS_LEVEL_PARENT = 0,
    /* Main application process, which starts the python interpreter and
     * runs user's program. In onefile builds, this is a child process
     * of parent/launcher process. In onedir builds, this is "top-level"
     * process. */
    PYI_PROCESS_LEVEL_MAIN = 1,
    /* A sub-process spawned from the main application process using the
     * same executable (e.g., spawned using sys.executable; for example,
     * a multiprocessing worker process). */
    PYI_PROCESS_LEVEL_SUBPROCESS = 2
};


struct PYI_CONTEXT
{
    /* Command line arguments passed to the application.
     *
     * On Windows, these are wide-char (UTF-16) strings, which can be
     * directly passed into python's configuration structure.
     *
     * On POSIX systems, the strings are in local 8-bit encoding, and we
     * will need to convert them to wide-char strings when setting up
     * python's configuration structure. But in POSIX codepath, the 8-bit
     * strings from `argv` are also used in other places, for example,
     * when trying to resolve the executable's true location, and when
     * spawning child process in onefile mode. */
#ifdef _WIN32
    int argc;
    wchar_t **argv_w;
#else
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
     * These two fields are initialized only if needed, for example in
     * codepaths that involve macOS app bundles. Look for calls to the
     * `pyi_utils_initialize_args` function.
     *
     * While setting up the embedded python interpreter configuration,
     * the corresponding codepath automatically chooses between argc/argv
     * and pyi_argc/pyi_argv depending on the availability of the latter.
     * This means that if `pyi_utils_initialize_args` was called at
     * some point before, the modified arguments are passed on to the
     * python interpreter (and will appear in sys.argv).
     *
     * Similarly, when spawning the child process of a onefile application,
     * we pass pyi_argv to the `execvp` call if available, and if not,
     * we use the original argv. */
    int pyi_argc;
    char **pyi_argv;
#endif /* ifdef _WIN32 */

    /* Fully resolved path to the executable */
    char executable_filename[PYI_PATH_MAX];

    /* Fully resolved path to the main PKG archive */
    char archive_filename[PYI_PATH_MAX];

    /* Main PKG archive */
    struct ARCHIVE *archive;

    /* Flag indicating whether application contains resources for
     * displaying splash screen or not. This does not reflect the
     * actual run-time state of the splash screen (which might be
     * suppressed, or fail to initialize). */
    unsigned char has_splash;

    /* Flag indicating whether user explicitly requested suppression
     * of splash screen via `PYINSTALLER_SUPPRESS_SPLASH_SCREEN`
     * environment variable. */
    unsigned char suppress_splash;

    /* Splash screen context structure. */
    struct SPLASH_CONTEXT *splash;

    /* Flag indicating whether the application's main PKG archive has
     * onefile semantics or not (i.e., needs to extract files to
     * temporary directory and run a child process). In addition to
     * onefile applications themselves, this also applies to applications
     * that used MERGE() for multi-package. */
    unsigned char is_onefile;

    /* Process level of this process. See definitions of PYI_PROCESS_LEVEL
     * enum. Used to determine whether onefile process should unpack
     * itself or expect to already be unpacked, whether splash screen
     * should be set up or not, etc.
     *
     * NOTE: we need to use signed integral type here, and on some
     * platforms (e.g., AIX), `char` behaves like `unsigned char` by
     * default - to avoid potential issues, explicitly use `signed char`. */
    signed char process_level;

    /* Process level of this process' parent process. See definitions
     * of PYI_PROCESS_LEVEL enum. */
    signed char parent_process_level;

    /* Application's top-level directory (sys._MEIPASS), where the data
     * and shared libraries are. For applications with onefile semantics,
     * this is ephemeral temporary directory where application unpacked
     * itself. */
    char application_home_dir[PYI_PATH_MAX];

    /* Structure encapsulating loaded python shared library and pointers
     * to imported functions. */
    struct DYLIB_PYTHON *dylib_python;

    /* Strict unpack mode for onefile builds. This flag is dynamically
     * controlled by `PYINSTALLER_STRICT_UNPACK_MODE` environment variable
     * (enabled by a value different from 0). If enabled, extraction of
     * onefile builds (either splash screen dependencies, or main archive
     * unpacking) fails if trying to overwrite an existing file. Otherwise,
     * a warning is displayed on stderr. This is primarily used for
     * run-time detection of duplicated resources in onefile archives on
     * PyInstaller's CI. */
    unsigned char strict_unpack_mode;

#if !defined(_WIN32)
    /* Path to the dynamic linker/loader; if executable is launched
     * via explicitly specified dynamic linker/loader (for example,
     * /lib64/ld-linux-x86-64.so.2 /path/to/executable), we need to
     * propagate its name into execvp() call. */
    char dynamic_loader_filename[PYI_PATH_MAX];
#endif /* !defined(_WIN32) */

#if defined(_WIN32)
    /* Security attributes structure with security descriptor that limits
     * the access to created directory to the user. Used in onefile mode
     * with `CreateDirectoryW` when creating the application's temporary
     * top-level directory and its sub-directories.
     *
     * Must be explicitly initialized by calling
     * `pyi_win32_initialize_security_descriptor`, and freed by calling
     * `pyi_win32_free_security_descriptor`. */
    SECURITY_ATTRIBUTES *security_attr;
#endif

    /* Child process (onefile mode) variables. */
#if defined(_WIN32)
    /* Child process information. */
    PROCESS_INFORMATION child_process;

    /* Hidden window used to receive session shutdown events
     * (WM_QUERYENDSESSION and WM_ENDSESSION messages). */
    HWND hidden_window;

    /* Flags used on Windows to signal various circumstances under which
     * the application should shut itself down (i.e., in onefile mode,
     * it should terminate the child process and perform the cleanup) */

    /* CTRL_CLOSE_EVENT, CTRL_SHUTDOWN_EVENT, or CTRL_LOGOFF_EVENT
     * received via installed console handler. */
    /* NOTE: marked as volatile because it is set in installed console
     * handler, and read in the main codepath. */
    volatile unsigned char console_shutdown;

    /* WM_QUERYENDSESSION received via hidden window. */
    unsigned char session_shutdown;
#else
    /* Process ID of the child process (onefile mode). Keeping track of
     * the child PID allows us to forward signals to the child. */
    /* NOTE: marked as volatile because it is read in the POSIX signal
     * handler. */
    volatile pid_t child_pid;

    /* Remember whether child has received a signal and what signal it was.
     * In onefile mode, this allows us to re-raise the signal in the parent
     * once the temporary directory has been cleaned up. */
    int child_signalled;
    int child_signal;

#if defined(LAUNCH_DEBUG)
    /* Basic statistics for forwarding signal handler:
     *  - number of received signals (number of times the handler was called)
     *  - number of successfully forwarded signals
     *  - number of errors during forwarding (number of failed kill() calls)
     *  - number of no-op handler calls (with invalid child_pid).
     * All members are volatile due to being modified in signal handler. */
    volatile unsigned int signal_forward_all;
    volatile unsigned int signal_forward_ok;
    volatile unsigned int signal_forward_error;
    volatile unsigned int signal_forward_noop;
#endif /* defined(LAUNCH_DEBUG) */
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

    /**
     * Flag indicating that colleted python shared library was built
     * with --disable-gil / Py_GIL_DISABLED. Used to select correct
     * PyConfig structure layout, which contains additional `enable_gil`
     * field. */
    unsigned char nogil_enabled;

    /**
     * Apple Events handling in macOS .app bundles
     */
#if defined(__APPLE__) && defined(WINDOWED)
    struct APPLE_EVENT_HANDLER_CONTEXT *ae_ctx;
#endif
};

extern struct PYI_CONTEXT *const global_pyi_ctx;


int pyi_main(struct PYI_CONTEXT *pyi_ctx);

/* Used in both pyi_main.c and pyi_utils_win32.c */
int pyi_main_onefile_parent_cleanup(struct PYI_CONTEXT *pyi_ctx);


#endif /* PYI_MAIN_H */
