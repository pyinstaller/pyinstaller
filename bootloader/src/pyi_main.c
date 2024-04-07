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
 * Bootloader for a packed executable.
 */

#ifdef _WIN32
    #include <windows.h>
    #include <wchar.h>
#else
    #include <unistd.h>
    #include <signal.h>  /* raise */
    #include <errno.h>
#endif

#ifdef __CYGWIN__
    #include <sys/cygwin.h>  /* cygwin_conv_path */
    #include <windows.h>  /* SetDllDirectoryW */
#endif

#include <stdio.h>  /* FILE */
#include <stdlib.h> /* calloc */
#include <string.h> /* memset */

#if defined(__linux__)
    #include <sys/prctl.h> /* prctl() */
#endif

#if defined(__APPLE__) && defined(WINDOWED)
    #include <Carbon/Carbon.h>  /* TransformProcessType */
#endif

/* PyInstaller headers. */
#include "pyi_main.h"
#include "pyi_global.h"  /* PATH_MAX */
#include "pyi_path.h"
#include "pyi_archive.h"
#include "pyi_utils.h"
#include "pyi_pythonlib.h"
#include "pyi_launch.h"
#include "pyi_win32_utils.h"
#include "pyi_splash.h"
#include "pyi_apple_events.h"


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


/* Pointer to global PYI_CONTEXT structure. Intended for use in signal
 * handlers that have no user data / context */
PYI_CONTEXT *global_pyi_ctx = &_pyi_ctx;


/* Large parts of `pyi_main` are implemented as helper functions. We
 * keep their definitions below that of `pyi_main`, in an attempt to
 * keep code organized in top-down fashion. Hence, we need forward
 * declarations here */
static void _pyi_main_read_runtime_options(PYI_CONTEXT *pyi_ctx);

static int _pyi_main_onedir_or_onefile_child(PYI_CONTEXT *pyi_ctx);
static int _pyi_main_onefile_parent(PYI_CONTEXT *pyi_ctx);

static int _pyi_main_resolve_executable(PYI_CONTEXT *pyi_context);
static int _pyi_main_resolve_pkg_archive(PYI_CONTEXT *pyi_context);

#if !defined(_WIN32) && !defined(__APPLE__)
static int _pyi_main_handle_posix_onedir(PYI_CONTEXT *pyi_ctx);
#endif


int
pyi_main(PYI_CONTEXT *pyi_ctx)
{
#ifdef _WIN32
    /* On Windows, both Visual C runtime and MinGW seem to buffer stderr
     * when redirected. This might cause the output to not appear at all
     * if the application crashes or is terminated, which in turn makes
     * debugging difficult. So make sure that stderr is unbuffered. */
    setbuf(stderr, (char *)NULL);
#endif  /* _WIN32 */

    VS("PyInstaller Bootloader 6.x\n");

    /* Fully resolve the executable name. */
    if (_pyi_main_resolve_executable(pyi_ctx) < 0) {
        return -1;
    }
    VS("LOADER: executable file: %s\n", pyi_ctx->executable_filename);

    /* Resolve main PKG archive - embedded or side-loaded. */
    if (_pyi_main_resolve_pkg_archive(pyi_ctx) < 0) {
        return -1;
    }
    VS("LOADER: archive file: %s\n", pyi_ctx->archive_filename);

    /* We can now access PKG archive via pyi_ctx->archive; for example,
     * to read run-time options */

    /* First, check if archive contains extractable entries - this implies
     * that we are running in onefile mode */
    pyi_ctx->is_onefile = pyi_ctx->archive->contains_extractable_entries;
    pyi_ctx->needs_to_extract = pyi_ctx->is_onefile;

    /* Read all applicable run-time options from the PKG archive */
    _pyi_main_read_runtime_options(pyi_ctx);

    /* Early console hiding/minimization (Windows-only) */
#if defined(_WIN32) && !defined(WINDOWED)
    if (pyi_ctx->hide_console == PYI_HIDE_CONSOLE_HIDE_EARLY) {
        pyi_win32_hide_console();
    } else if (pyi_ctx->hide_console == PYI_HIDE_CONSOLE_MINIMIZE_EARLY) {
        pyi_win32_minimize_console();
    }
#endif

    /* Read the setting for strict unpack mode from corresponding
     * environment variable. */
    if (1) {
        char *env_strict = pyi_getenv("PYINSTALLER_STRICT_UNPACK_MODE"); /* strdup'd copy or NULL */
        if (env_strict) {
            pyi_ctx->strict_unpack_mode = strcmp(env_strict, "0") != 0;
            free(env_strict);
        }
    }

    /* On Linux, restore process name (passed from parent process via
     * environment variable. */
#if defined(__linux__)
    if (1) {
        char *processname = pyi_getenv("_PYI_LINUX_PROCESS_NAME");
        if (processname) {
            VS("LOADER: restoring process name: %s\n", processname);
            prctl(PR_SET_NAME, processname, 0, 0); /* Ignore failures */
        }
        free(processname);
        pyi_unsetenv("_PYI_LINUX_PROCESS_NAME");
    }
#endif  /* defined(__linux__) */

    /* Infer the process type (onefile parent, onefile child, onedir),
     * and based on that, determine the application's top-level directory. */
    if (pyi_ctx->is_onefile) {
        char *meipass2_value = NULL;

        VS("LOADER: application has onefile semantics...\n");

        /* Check if PyInstaller's environment has already been set. This
         * indicates that we are in the child process, and we do not need
         * to extract files. */

        /* On Windows, environment variables are set/retrieved via
         * wide-char API, and encoded/decoded to/from UTF8, so the path
         * here is unicode. On POSIX systems, the local 8-bit encoding
         * is used. */
        meipass2_value = pyi_getenv("_MEIPASS2");
        VS("LOADER: _MEIPASS2 is %s\n", (meipass2_value ? meipass2_value : "not set"));

        /* Clear the _MEIPASS2 variable; if application were to spawn
         * another PyInstaller onefile application as a subprocess, that
         * instance must not be fooled into thinking that it has already
         * been unpacked. */
        pyi_unsetenv("_MEIPASS2");

        if (meipass2_value && meipass2_value[0]) {
            /* This is a child process; reset the needs-to-extract flag */
            VS("LOADER: this is child process of onefile application.\n");
            pyi_ctx->needs_to_extract = 0;

            /* Copy the application's top-level directory from environment */
            if (snprintf(pyi_ctx->application_home_dir, PATH_MAX, "%s", meipass2_value) >= PATH_MAX) {
                FATALERROR("Path exceeds PATH_MAX limit.\n");
                return -1;
            }

            free(meipass2_value);
        } else {
            VS("LOADER: this is parent process of onefile application.\n");

            /* On Windows, initialize security descriptor for temporary directory.
             * This is required by `pyi_win32_mkdir()` calls made when creating application's
             * temporary directory and its sub-directories during file extration. */
#if defined(_WIN32)
            VS("LOADER: initializing security descriptor for temporary directory...\n");
            if (pyi_win32_initialize_security_descriptor(pyi_ctx) == -1) {
                FATALERROR("Failed to initialize security descriptor for temporary directory!\n");
                return -1;
            }
#endif

            /* Create temporary directory */
            VS("LOADER: creating temporary directory (runtime_tmpdir=%s)...\n", pyi_ctx->runtime_tmpdir);

            if (pyi_create_temporary_application_directory(pyi_ctx) < 0) {
                FATALERROR("Could not create temporary directory!\n");
                return -1;
            }

            VS("LOADER: created temporary directory: %s\n", pyi_ctx->application_home_dir);
        }
    } else {
        char executable_dir[PATH_MAX];
        bool is_macos_app_bundle = false;
#if defined(__APPLE__)
        size_t executable_dir_len;
#endif

        VS("LOADER: application has onedir semantics...\n");

        /* Determine application's top-level directory based on the
         * executable's location. */
        pyi_path_dirname(executable_dir, pyi_ctx->executable_filename);

#if defined(__APPLE__)
        executable_dir_len = strnlen(executable_dir, PATH_MAX);
        is_macos_app_bundle = executable_dir_len > 19 && strncmp(executable_dir + executable_dir_len - 19, ".app/Contents/MacOS", 19) == 0;
#endif

        if (is_macos_app_bundle) {
            /* macOS .app bundle; relocate top-level application directory
             * from Contents/MacOS directory to Contents/Frameworks */
            char contents_dir[PATH_MAX]; /* the parent Contents directory */
            pyi_path_dirname(contents_dir, executable_dir);
            pyi_path_join(pyi_ctx->application_home_dir, contents_dir, "Frameworks");
        } else {
            if (pyi_ctx->contents_subdirectory) {
                pyi_path_join(pyi_ctx->application_home_dir, executable_dir, pyi_ctx->contents_subdirectory);
            } else {
                snprintf(pyi_ctx->application_home_dir, PATH_MAX, "%s", executable_dir);
            }
        }

        /* Special handling for onedir mode on POSIX systems other than
         * macOS. To achieve single-process onedir mode, we need to set
         * library search path and restart the current process. This is
         * handled by the following helper function. */
#if !defined(_WIN32) && !defined(__APPLE__)
        _pyi_main_handle_posix_onedir(pyi_ctx);
#endif
    }

    VS("LOADER: application's top-level directory: %s\n", pyi_ctx->application_home_dir);

    /* On Windows and under cygwin, add application's top-level directory
     * to DLL search path.  */
#if defined(_WIN32) || defined(__CYGWIN__)
    if (1) {
        wchar_t dllpath_w[PATH_MAX];

#if defined(__CYGWIN__)
        /* Cygwin */
        ret = cygwin_conv_path(CCP_POSIX_TO_WIN_W | CCP_RELATIVE, pyi_ctx->application_home_dir, dllpath_w, PATH_MAX);
        if (ret != 0) {
            FATAL_PERROR("cygwin_conv_path", "Failed to convert DLL search path!\n");
            return -1;
        }
#else
        /* Windows */
        if (pyi_win32_utils_from_utf8(dllpath_w, pyi_ctx->application_home_dir, PATH_MAX) == NULL) {
            FATALERROR("Failed to convert DLL search path!\n");
            return -1;
        }
#endif  /* defined(__CYGWIN__) */

        VS("LOADER: calling SetDllDirectory: %S\n", dllpath_w);
        SetDllDirectoryW(dllpath_w);
    }
#endif  /* defined(_WIN32) || defined(__CYGWIN__) */

    /* Check if splash screen is available and should be displayed. It
     * should be displayed by the parent process of onefile application,
     * and in onedir process. In other words, everywhere but in onefile
     * child process. */
    if (!(pyi_ctx->is_onefile && !pyi_ctx->needs_to_extract)) {
        VS("LOADER: looking for splash screen resources...\n");
        pyi_ctx->splash = pyi_splash_context_new();
        if (pyi_splash_setup(pyi_ctx->splash, pyi_ctx) == 0) {
            int ret = 0;

            /* Splash screen resources found; setup up splash screen */
            VS("LOADER: setting up splash screen...\n");

            /* In onefile mode, we need to extract dependencies (shared
             * libraries, .tcl files, etc.) from PKG archive. */
            if (pyi_ctx->is_onefile) {
                VS("LOADER: extracting splash screen dependencies...\n");
                ret = pyi_splash_extract(pyi_ctx->splash, pyi_ctx);
                if (ret != 0) {
                    OTHERERROR("Failed to unpack splash screen dependencies from PKG archive!\n");
                }
            }

            /* Load Tcl/Tk shared libraries */
            if (ret == 0) {
                ret = pyi_splash_load_shared_libaries(pyi_ctx->splash);
                if (ret != 0) {
                    OTHERERROR("Failed to load Tcl/Tk shared libraries for splash screen!\n");
                }
            }

            /* Finally, start the splash screen */
            if (ret == 0) {
                ret = pyi_splash_start(pyi_ctx->splash, pyi_ctx->executable_filename);
                if (ret != 0) {
                    OTHERERROR("Failed to start splash screen!\n");
                }
            }

            if (ret != 0) {
                /* Either we failed to extract splash resources, or
                 * failed to load Tcl/Tk shared libraries. Clean up
                 * the state by finalizing it, and free the allocated
                 * structure. */
                pyi_splash_finalize(pyi_ctx->splash);
                pyi_splash_context_free(&pyi_ctx->splash);
            }
        } else {
            /* Splash screen resources not found */
            VS("LOADER: splash screen resources not found.\n");
            pyi_splash_context_free(&pyi_ctx->splash);
        }
    }

    /* Split execution between onefile parent process vs. onefile child
     * process / onedir process. */
    if (pyi_ctx->needs_to_extract) {
        /* Onefile parent */
        return _pyi_main_onefile_parent(pyi_ctx);
    } else {
        /* Onedir or onefile child */
        return _pyi_main_onedir_or_onefile_child(pyi_ctx);
    }
}

static void
_pyi_main_read_runtime_options(PYI_CONTEXT *pyi_ctx)
{
    const ARCHIVE *archive = pyi_ctx->archive;
    const TOC_ENTRY *toc_entry;

    for (toc_entry = archive->toc; toc_entry < archive->toc_end; toc_entry = pyi_archive_next_toc_entry(archive, toc_entry)) {
        if (toc_entry->typecode != ARCHIVE_ITEM_RUNTIME_OPTION) {
            continue;
        }

        /* NOTE: option names are constants, so we use hard-coded
         * lengths as well to avoid invoking strlen() on each
         * comparison. */

        /* pyi-runtime-tmpdir <value>
         *
         * Run-time temporary directory override for onefile programs. */
        if (strncmp(toc_entry->name, "pyi-runtime-tmpdir", 18) == 0) {
            pyi_ctx->runtime_tmpdir = toc_entry->name + 19;
        }

        /* pyi-contents-directory <value>
         *
         * Contents sub-directory in onedir programs. */
        if (strncmp(toc_entry->name, "pyi-contents-directory", 22) == 0) {
            pyi_ctx->contents_subdirectory = toc_entry->name + 23;
        }

        /* pyi-macos-argv-emulation
         *
         * Argv emulation for macOS .app bundles. */
#if defined(__APPLE__) && defined(WINDOWED)
        if (strncmp(toc_entry->name, "pyi-macos-argv-emulation", 24) == 0) {
            pyi_ctx->macos_argv_emulation = 1;
            continue;
        }
#endif

        /* pyi-hide-console <value>
         *
         * Console hiding/minimization option for Windows console-enabled
         * builds. */
#if defined(_WIN32) && !defined(WINDOWED)
        if (strncmp(toc_entry->name, "pyi-hide-console", 16) == 0) {
            const char *option_value = toc_entry->name + 17;
            if (strcmp(option_value, HIDE_CONSOLE_OPTION_HIDE_EARLY) == 0) {
                pyi_ctx->hide_console = PYI_HIDE_CONSOLE_HIDE_EARLY;
            } else if (strcmp(option_value, HIDE_CONSOLE_OPTION_MINIMIZE_EARLY) == 0) {
                pyi_ctx->hide_console = PYI_HIDE_CONSOLE_MINIMIZE_EARLY;
            } else if (strcmp(option_value, HIDE_CONSOLE_OPTION_HIDE_LATE) == 0) {
                pyi_ctx->hide_console = PYI_HIDE_CONSOLE_HIDE_LATE;
            } else if (strcmp(option_value, HIDE_CONSOLE_OPTION_MINIMIZE_LATE) == 0) {
                pyi_ctx->hide_console = PYI_HIDE_CONSOLE_MINIMIZE_LATE;
            } else {
                pyi_ctx->hide_console = PYI_HIDE_CONSOLE_UNUSED;
            }
            continue;
        }
#endif

        /* pyi-disable-windowed-traceback
         *
         * Disable traceback in the unhandled exception message in
         * windowed/noconsole builds (unhandled exception dialog in
         * Windows noconsole builds, syslog message in macOS .app
         * bundles) */
#if defined(WINDOWED)
        if (strncmp(toc_entry->name, "pyi-disable-windowed-traceback", 30) == 0) {
            pyi_ctx->disable_windowed_traceback = 1;
            continue;
        }
#endif

        /* pyi-bootloader-ignore-signals
         *
         * Ignore signals in onefile parent process (POSIX only) */
#if !defined(_WIN32)
        if (strncmp(toc_entry->name, "pyi-bootloader-ignore-signals", 29) == 0) {
            pyi_ctx->ignore_signals = 1;
            continue;
        }
#endif
    }
}


/**********************************************************************\
 *                  Onedir or onefile child codepath                  *
\**********************************************************************/
static int
_pyi_main_onedir_or_onefile_child(PYI_CONTEXT *pyi_ctx)
{
    int ret;

    /* Argument processing and argv emulation for onedir macOS .app bundles.
     * In onefile mode, this step was performed by the parent, and extra
     * arguments were passed to argv/argc when spawning child process. */
#if defined(__APPLE__) && defined(WINDOWED)
    if (!pyi_ctx->is_onefile) {
        /* Initialize pyi_argc and pyi_argv with original argc and argv.
         * Do this regardless of argv-emulation setting, because
         * pyi_utils_initialize_args() also filters out -psn_xxx argument. */
        if (pyi_utils_initialize_args(pyi_ctx, pyi_ctx->argc, pyi_ctx->argv) < 0) {
            return -1;
        }

        /* Optional argv emulation for onedir .app bundles */
        if (pyi_ctx->macos_argv_emulation) {
            /* Install event handlers */
            pyi_apple_install_event_handlers(pyi_ctx);
            /* Process Apple events; this updates argc_pyi/argv_pyi
             * accordingly */
            pyi_apple_process_events(&pyi_ctx->ae_ctx, 0.25);  /* short_timeout (250 ms) */
            /* Uninstall event handlers */
            pyi_apple_uninstall_event_handlers(&pyi_ctx->ae_ctx);
            /* The processing of Apple events swallows up the initial
             * activation event, whatever it might have been (typically
             * oapp, but could also be odoc or GURL if application is
             * launched in response to request to open file/URL).
             * This seems to cause issues with some UI frameworks
             * (Tcl/Tk, in particular); so we submit a new oapp event
             * to ourselves... */
            pyi_apple_submit_oapp_event(&pyi_ctx->ae_ctx);
        }
    }
#endif

    /* Late console hiding/minimization; this should turn out to be a
     * no-op in child processes of onefile programs or in spawned
     * additional subprocesses using the executable, because the
     * process does not own the console. */
#if defined(_WIN32) && !defined(WINDOWED)
    if (pyi_ctx->hide_console == PYI_HIDE_CONSOLE_HIDE_LATE) {
        pyi_win32_hide_console();
    } else if (pyi_ctx->hide_console == PYI_HIDE_CONSOLE_MINIMIZE_LATE) {
        pyi_win32_minimize_console();
    }
#endif

    /* Use message queue to have Windows stop showing spinning-wheel
     * cursor indicating that the program is starting. For details,
     * see the corresponding comment in the onefile parent code-path.
     *
     * In onedir mode, this aims to make noconsole programs that do
     * not display any UI appear to start faster.
     */
#if defined(_WIN32) && defined(WINDOWED)
    if (pyi_ctx->splash == NULL) {
        MSG msg;
        PostMessageW(NULL, 0, 0, 0);
        GetMessageW(&msg, NULL, 0, 0);
    }
#endif

    /* Main code to initialize Python and run user's code. */
    pyi_launch_initialize(pyi_ctx);
    ret = pyi_launch_execute(pyi_ctx);
    pyi_launch_finalize(pyi_ctx);

    /* Clean up splash screen resources; required when in single-process
     * execution mode, i.e. when using --onedir on Windows or macOS. */
    pyi_splash_finalize(pyi_ctx->splash);
    pyi_splash_context_free(&pyi_ctx->splash);

#if defined(__APPLE__) && defined(WINDOWED)
    /* Clean up arguments that were used with Apple event processing .*/
    pyi_utils_free_args(pyi_ctx);
#endif

    return ret;
}


/**********************************************************************\
 *                      Onefile parent codepath                       *
\**********************************************************************/
static int
_pyi_main_onefile_parent(PYI_CONTEXT *pyi_ctx)
{
    int ret;

    /* Extract files to temporary directory */
    VS("LOADER: extracting files to temporary directory...\n");
    if (pyi_launch_extract_files_from_archive(pyi_ctx) < 0) {
        VS("LOADER: failed to extract files!\n");
        return -1;
    }

    /* At this point, extraction to temporary directory is complete,
     * and we can free the Windows security descriptor that was used
     * during creation of temporary directory and its sub-directories. */
#if defined(_WIN32)
    pyi_win32_free_security_descriptor(pyi_ctx);
#endif

    /* Late console hiding/minimization */
#if defined(_WIN32) && !defined(WINDOWED)
    if (pyi_ctx->hide_console == PYI_HIDE_CONSOLE_HIDE_LATE) {
        pyi_win32_hide_console();
    } else if (pyi_ctx->hide_console == PYI_HIDE_CONSOLE_MINIMIZE_LATE) {
        pyi_win32_minimize_console();
    }
#endif

    /* On Linux, pass the current process name to the child process,
     * via custom environment variable. */
#if defined(__linux__)
    if (1) {
        char processname[16]; /* 16 bytes as per prctl() man page */

        /* Pass the process name to child via environment variable. */
        if (!prctl(PR_GET_NAME, processname, 0, 0)) {
            VS("LOADER: storing process name: %s\n", processname);
            pyi_setenv("_PYI_LINUX_PROCESS_NAME", processname);
        }
    }
#endif  /* defined(__linux__) */

    /* On OSes other than Windows and macOS, we need to set library
     * search path (via LD_LIBRARY_PATH or equivalent). Since the
     * search path cannot be modified for the running process, we
     * need to set it in the parent process, before launching the
     * child process. */
#if !defined(_WIN32) && !defined(__APPLE__)
    if (pyi_utils_set_library_search_path(pyi_ctx->application_home_dir) == -1) {
        return -1;
    }
#endif /* !defined(_WIN32) && !defined(__APPLE__) */

    /* When a windowed/noconsole process is launched on Windows, the
     * OS displays a spinning-wheel cursor to indicate that the program
     * is starting. This goes on for a fixed amount of time or until
     * the process uses some UI functionality (creates a window, uses
     * message queue). In a PyInstaller onefile application, the parent
     * process displays a window only if splash screen is used; the UI
     * is created and shown by the child process. To prevent the
     * "program is starting" cursor being shown for the full duration
     * (i.e., after the child process shows its UI), make use of
     * message queue to signal the OS that the process is alive.
     *
     * For onefile, we do this just before we spawn the child process,
     * so that the "program is starting" cursor is shown while the
     * parent process unpacks the application.
     *
     * See: https://github.com/python/cpython/blob/v3.12.2/PC/launcher.c#L765-L779
     */
#if defined(_WIN32) && defined(WINDOWED)
    if (pyi_ctx->splash == NULL) {
        MSG msg;
        PostMessageW(NULL, 0, 0, 0);
        GetMessageW(&msg, NULL, 0, 0);
    }
#endif

    /* On macOS, transform this (parent) process into background
     * process. */
#if defined(__APPLE__) && defined(WINDOWED)
    if (1) {
        ProcessSerialNumber psn = { 0, kCurrentProcess };
        OSStatus returnCode = TransformProcessType(&psn, kProcessTransformToBackgroundApplication);
    }
#endif

    /* Pass top-level application directory (the temporary directory
     * where files were extracted) to the child process via
     * corresponding environment variable. */
    VS("LOADER: setting _MEIPASS2 to %s\n", pyi_ctx->application_home_dir);
    pyi_setenv("_MEIPASS2", pyi_ctx->application_home_dir);

    /* Start the child process that will execute user's program. */
    VS("LOADER: starting the child process...\n");
    ret = pyi_utils_create_child(pyi_ctx);

    VS("LOADER: child process exited (return code: %d)\n", ret);

    VS("LOADER: performing cleanup...\n");

    /* Finalize splash screen before temp directory gets wiped, since the splash
     * screen might hold handles to shared libraries inside the temp dir. Those
     * wouldn't be removed, leaving the temp folder behind. */
    pyi_splash_finalize(pyi_ctx->splash);
    pyi_splash_context_free(&pyi_ctx->splash);

    /* Delete the application's temporary directory */
    if (pyi_recursive_rmdir(pyi_ctx->application_home_dir) < 0) {
        OTHERERROR("WARNING: failed to remove temporary directory: %s\n", pyi_ctx->application_home_dir);
    }

    /* Clean up the archive structure */
    pyi_archive_free(&pyi_ctx->archive);

    /* Re-raise child's signal, if necessary (POSIX only) */
#ifndef _WIN32
    if (pyi_ctx->child_signalled) {
        VS("LOADER: re-raising child signal %d\n", pyi_ctx->child_signal);
        raise(pyi_ctx->child_signal);
    }
#endif

    return ret;
}


/**********************************************************************\
 *                     Executable file resolution                     *
\**********************************************************************/
#ifdef _WIN32

static int
_pyi_resolve_executable_win32(char *executable_filename)
{
    wchar_t modulename_w[PATH_MAX];

    /* GetModuleFileNameW returns an absolute, fully qualified path */
    if (!GetModuleFileNameW(NULL, modulename_w, PATH_MAX)) {
        FATAL_WINERROR("GetModuleFileNameW", "Failed to obtain executable path.\n");
        return -1;
    }

    /* If path is a symbolic link, resolve it */
    if (pyi_win32_is_symlink(modulename_w)) {
        wchar_t executable_filename_w[PATH_MAX];
        int offset = 0;

        VS("LOADER: executable file %S is a symbolic link - resolving...\n", modulename_w);

        /* Resolve */
        if (pyi_win32_realpath(modulename_w, executable_filename_w) < 0) {
            VS("LOADER: failed to resolve full path for %s\n", modulename_w);
            return -1;
        }

        /* Remove the extended path indicator, to avoid potential issues due
         * to its appearance in `sys.executable`, `sys._MEIPASS`, etc. */
        if (wcsncmp(L"\\\\?\\", executable_filename_w, 4) == 0) {
            offset = 4;
        }

        /* Convert to UTF-8 */
        if (!pyi_win32_utils_to_utf8(executable_filename, executable_filename_w + offset, PATH_MAX)) {
            FATALERROR("Failed to convert executable path to UTF-8.\n");
            return -1;
        }
    } else {
        /* Convert to UTF-8 */
        if (!pyi_win32_utils_to_utf8(executable_filename, modulename_w, PATH_MAX)) {
            FATALERROR("Failed to convert executable path to UTF-8.\n");
            return -1;
        }
    }

    return 0;
}

#elif __APPLE__

static int
_pyi_resolve_executable_macos(char *executable_filename)
{
    char program_path[PATH_MAX];
    uint32_t name_length = sizeof(program_path);

    /* Mac OS X has special function to obtain path to executable.
     * This may return a symbolic link. */
    if (_NSGetExecutablePath(program_path, &name_length) != 0) {
        FATALERROR("Failed to obtain executable path via _NSGetExecutablePath!\n");
        return -1;
    }

    /* Canonicalize the filename and resolve symbolic links */
    if (realpath(program_path, executable_filename) == NULL) {
        VS("LOADER: failed to resolve full path for %s\n", program_path);
        return -1;
    }

    return 0;
}

#else

#if defined(__linux__)

/* Return 1 if the given executable name is in fact the ld.so dynamic loader. */
static bool
_pyi_is_ld_linux_so(const char *filename)
{
    char basename[PATH_MAX];
    int status;
    char loader_name[65] = "";
    int soversion = 0;

    pyi_path_basename(basename, filename);

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

/* Search $PATH for the program with the given name, and return its full path. */
static bool
_pyi_find_progam_in_search_path(const char *name, char *result_path)
{
    char *search_paths = pyi_getenv("PATH"); // returns a copy
    char *search_path;

    if (search_paths == NULL) {
        return false;
    }

    search_path = strtok(search_paths, PYI_PATHSEPSTR);
    while (search_path != NULL) {
        if ((pyi_path_join(result_path, search_path, name) != NULL) && pyi_path_exists(result_path)) {
            free(search_paths);
            return true;
        }
        search_path = strtok(NULL, PYI_PATHSEPSTR);
    }

    free(search_paths);
    return false;
}

static int
_pyi_resolve_executable_posix(const char *argv0, char *executable_filename)
{
    /* On Linux, Cygwin, FreeBSD, and Solaris, we try /proc entry first.
     * The entry points at "true" file location, i.e., fully canonicalized
     * and with all symbolic links resolved. */
    ssize_t name_len = -1;

#if defined(__linux__) || defined(__CYGWIN__)
    name_len = readlink("/proc/self/exe", executable_filename, PATH_MAX - 1);  /* Linux, Cygwin */
#elif defined(__FreeBSD__)
    name_len = readlink("/proc/curproc/file", executable_filename, PATH_MAX - 1);  /* FreeBSD */
#elif defined(__sun)
    name_len = readlink("/proc/self/path/a.out", executable_filename, PATH_MAX - 1);  /* Solaris */
#endif

    if (name_len != -1) {
        /* Output is not yet NULL-terminated, so we need to do it using returned byte count. */
        executable_filename[name_len] = 0;
    }

    /* On linux, we might have been launched using custom ld.so dynamic loader.
     * In that case, /proc/self/exe points to the ld.so executable, and we need
     * to ignore it. */
#if defined(__linux__)
    if (_pyi_is_ld_linux_so(executable_filename) == true) {
        VS("LOADER: resolved executable file %s is ld.so dynamic loader - ignoring it!\n", executable_filename);
        name_len = -1;
    }
#endif

    if (name_len != -1) {
        return 0;
    }

    /* We failed to resolve the executable file via /proc (or we were
     * launched via ld.so dynamic loader). Try to manually resolve the
     * program path/name given via argv[0]. */
    if (strchr(argv0, PYI_SEP)) {
        /* Absolute or relative path was given. Canonicalize it, and
         * resolve symbolic links. */
        VS("LOADER: resolving program path from argv[0]: %s\n", argv0);
        if (realpath(argv0, executable_filename) == NULL) {
            VS("LOADER: failed to resolve full path for %s\n", argv0);
            return -1;
        }
    } else {
        /* No path, just program name. Search $PATH for executable with
         * matching name. */
        char program_path[PATH_MAX];

        if (_pyi_find_progam_in_search_path(argv0, program_path)) {
            /* Program found in $PATH; resolve full path */
            VS("LOADER: program %s found in PATH: %s. Resolving full path...\n", argv0, program_path);
            if (realpath(program_path, executable_filename) == NULL) {
                VS("LOADER: failed to resolve full path for %s\n", program_path);
                return -1;
            }
        } else {
            /* Searching $PATH failed; try resolving the name as-is,
             * and hope for the best. NOTE: can we even reach this part?
             * How was the executable even launched in such case? */
            VS("LOADER: could not find %s in $PATH! Attempting to resolve as-is...\n", argv0);
            if (realpath(argv0, executable_filename) == NULL) {
                VS("LOADER: failed to resolve full path for %s\n", argv0);
                return -1;
            }
        }
    }

    return 0;
}

#endif


static int
_pyi_main_resolve_executable(PYI_CONTEXT *pyi_ctx)
{
    /* Resolve using OS-specific implementation */
#ifdef _WIN32
    return _pyi_resolve_executable_win32(pyi_ctx->executable_filename);
#elif __APPLE__
    return _pyi_resolve_executable_macos(pyi_ctx->executable_filename);
#else
    return _pyi_resolve_executable_posix(pyi_ctx->argv[0], pyi_ctx->executable_filename);
#endif
}


/**********************************************************************\
 *                      Archive file resolution                       *
\**********************************************************************/
static int
_pyi_allow_pkg_sideload(const char *executable)
{
    FILE *file = NULL;
    uint64_t magic_offset;
    unsigned char magic[8];

    /* First, find the PKG sideload signature in the executable */
    file = pyi_path_fopen(executable, "rb");
    if (!file) {
        return -1;
    }

    /* Prepare magic pattern */
    memcpy(magic, MAGIC_BASE, sizeof(magic));
    magic[3] += 0x0D;  /* 0x00 -> 0x0D */

    /* Find magic pattern in the executable */
    magic_offset = pyi_utils_find_magic_pattern(file, magic, sizeof(magic));
    if (magic_offset == 0) {
        fclose(file);
        return 1; /* Error code 1: no embedded PKG sideload signature */
    }

    /* TODO: expand the verification by embedding hash of the PKG file */

    /* Allow PKG to be sideloaded */
    return 0;
}

static int
_pyi_main_resolve_pkg_archive(PYI_CONTEXT *pyi_ctx)
{
    int status;

    /* Try opening embedded archive first */
    VS("LOADER: trying to load executable-embedded archive...\n");
    pyi_ctx->archive = pyi_archive_open(pyi_ctx->executable_filename);
    if (pyi_ctx->archive != NULL) {
        /* Copy executable filename to archive filename; we know it does not exceed PATH_MAX */
        snprintf(pyi_ctx->archive_filename, PATH_MAX, "%s", pyi_ctx->executable_filename);
        return 0;
    }

    VS("LOADER: failed to open executable-embedded archive!\n");

    /* Check if side-load is allowed */
    status = _pyi_allow_pkg_sideload(pyi_ctx->executable_filename);
    if (status != 0) {
        VS("LOADER: side-load is disabled (code %d)!\n", status);
        FATALERROR(
            "Could not load PyInstaller's embedded PKG archive from the executable (%s)\n",
            pyi_ctx->executable_filename
        );
        return -1;
    }

    /* Infer the archive filename in side-load mode. On Windows, the .exe
     * suffix is replaced with .pkg, while elsewhere, .pkg suffix is
     * appended to the executable file name. */
#ifdef _WIN32
    snprintf(pyi_ctx->archive_filename, PATH_MAX, "%s", pyi_ctx->executable_filename);
    strcpy(pyi_ctx->archive_filename + strlen(pyi_ctx->archive_filename) - 3, "pkg");
#else
    if (snprintf(pyi_ctx->archive_filename, PATH_MAX, "%s.pkg", pyi_ctx->executable_filename) >= PATH_MAX) {
        return -1;
    }
#endif

    VS("LOADER: trying to load external PKG archive (%s)...\n", pyi_ctx->archive_filename);

    pyi_ctx->archive = pyi_archive_open(pyi_ctx->archive_filename);
    if (pyi_ctx->archive == NULL) {
        FATALERROR(
            "Could not side-load PyInstaller's PKG archive from external file (%s)\n",
            pyi_ctx->archive_filename
        );
        return -1;
    }

    return 0;
}


/**********************************************************************\
 *                 POSIX single-process onedir helper                 *
\**********************************************************************/
#if !defined(_WIN32) && !defined(__APPLE__)

/* On POSIX systems, we cannot dynamically set library search path for
 * the running process. On OSes other than macOS (where we solve this
 * by rewriting library paths in collected binaries), we therefore
 * achieve single-process onedir mode by setting the search-path
 * environment variable (i.e., `LD_LIBRARY_PATH`) and then restart/replace
 * the current process via `exec()` without `fork()` for the environment
 * changes (library search path) to take effect. We use a special
 * environment variable to keep track of whether the process has already
 * been restarted or not. */
static int
_pyi_main_handle_posix_onedir(PYI_CONTEXT *pyi_ctx)
{
    char *env_variable;
    int already_restarted;

    /* Check the environment variable */
    env_variable = pyi_getenv("_PYI_POSIX_ONEDIR_MODE");
    already_restarted = env_variable && strcmp(env_variable, "1") == 0;
    free(env_variable);

    pyi_unsetenv("_PYI_POSIX_ONEDIR_MODE");

    if (already_restarted) {
        VS("LOADER: POSIX onedir process has already restarted itself.\n");
        return 0;
    }

    VS("LOADER: POSIX onedir process needs to set library seach path and restart itself.\n");

    /* Set up the library search path (by modifying LD_LIBRARY_PATH or
     * equivalent), so that the restarted process will be able to find
     * the collected libraries in the top-level application directory. */
    if (pyi_utils_set_library_search_path(pyi_ctx->application_home_dir) < 0) {
        return -1;
    }

    /* Set environment variable to signal the bootloader that the process
     * has already been restarted. */
    pyi_setenv("_PYI_POSIX_ONEDIR_MODE", "1");

    /* Restart the process, by calling execvp() without fork(). */
    /* NOTE: the codepath that ended up here does not perform any
     * argument modification, so we always use pyi_ctx->argv (as
     * pyi_ctx->pyi_argv is unavailable). */
    if (execvp(pyi_ctx->executable_filename, pyi_ctx->argv) < 0) {
        OTHERERROR("LOADER: failed to restart process via execvp: %s\n", strerror(errno));
        return -1;
    }

    /* Unreachable */
    return 0;
}

#endif
