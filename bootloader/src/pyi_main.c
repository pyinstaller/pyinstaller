/*
 * ****************************************************************************
 * Copyright (c) 2013-2024, PyInstaller Development Team.
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

#if defined(__APPLE__)
    #include <mach-o/dyld.h>  /* _NSGetExecutablePath() */
#endif

/* PyInstaller headers. */
#include "pyi_main.h"
#include "pyi_global.h"  /* PYI_PATH_MAX */
#include "pyi_path.h"
#include "pyi_archive.h"
#include "pyi_utils.h"
#include "pyi_pythonlib.h"
#include "pyi_launch.h"
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
static struct PYI_CONTEXT _pyi_ctx;


/* Pointer to global PYI_CONTEXT structure. Intended for use in signal
 * handlers that have no user data / context */
struct PYI_CONTEXT *const global_pyi_ctx = &_pyi_ctx;


/* Large parts of `pyi_main` are implemented as helper functions. We
 * keep their definitions below that of `pyi_main`, in an attempt to
 * keep code organized in top-down fashion. Hence, we need forward
 * declarations here */
#if defined(LAUNCH_DEBUG)
static void _pyi_main_dump_command_line_arguments(const struct PYI_CONTEXT *pyi_ctx);
#endif

static void _pyi_main_read_runtime_options(struct PYI_CONTEXT *pyi_ctx);

static void _pyi_main_setup_splash_screen(struct PYI_CONTEXT *pyi_ctx);

static int _pyi_main_onedir_or_onefile_child(struct PYI_CONTEXT *pyi_ctx);
static int _pyi_main_onefile_parent(struct PYI_CONTEXT *pyi_ctx);

static int _pyi_main_resolve_executable(struct PYI_CONTEXT *pyi_context);
static int _pyi_main_resolve_pkg_archive(struct PYI_CONTEXT *pyi_context);

#if !defined(_WIN32) && !defined(__APPLE__) && !defined(__CYGWIN__)
static int _pyi_main_handle_posix_onedir(struct PYI_CONTEXT *pyi_ctx);
#endif


int
pyi_main(struct PYI_CONTEXT *pyi_ctx)
{
    char *env_var_value;
    bool reset_environment;

#ifdef _WIN32
    /* On Windows, both Visual C runtime and MinGW seem to buffer stderr
     * when redirected. This might cause the output to not appear at all
     * if the application crashes or is terminated, which in turn makes
     * debugging difficult. So make sure that stderr is unbuffered. */
    setbuf(stderr, (char *)NULL);
#endif  /* _WIN32 */

    PYI_DEBUG("PyInstaller Bootloader 6.x\n");

    /* In debug builds, dump the command-line arguments. */
#if defined(LAUNCH_DEBUG)
    _pyi_main_dump_command_line_arguments(pyi_ctx);
#endif

    /* Fully resolve the executable name. */
    if (_pyi_main_resolve_executable(pyi_ctx) < 0) {
        return -1;
    }
    PYI_DEBUG("LOADER: executable file: %s\n", pyi_ctx->executable_filename);

    /* Resolve main PKG archive - embedded or side-loaded. */
    if (_pyi_main_resolve_pkg_archive(pyi_ctx) < 0) {
        return -1;
    }
    PYI_DEBUG("LOADER: archive file: %s\n", pyi_ctx->archive_filename);

    /* We can now access PKG archive via pyi_ctx->archive; for example,
     * to read run-time options */

    /* Check if archive contains extractable entries - this implies
     * that we are running in onefile mode */
    pyi_ctx->is_onefile = pyi_ctx->archive->contains_extractable_entries;
    PYI_DEBUG("LOADER: application has %s semantics...\n", pyi_ctx->is_onefile ? "onefile" : "onedir");

    /* Check if user explicitly requested environment reset via the
     * PYINSTALLER_RESET_ENVIRONMENT environment variable. In this case,
     * we unconditionally reset the environment and make this process
     * a (new) top-level process. */
    reset_environment = false;

    env_var_value = pyi_getenv("PYINSTALLER_RESET_ENVIRONMENT");
    if (env_var_value) {
        /* Only valid value is 1; anything else is ignored */
        if (strcmp(env_var_value, "1") == 0) {
            PYI_DEBUG("LOADER: explicit environment reset enabled via environment variable!\n");
            reset_environment = true;
        }

        /* Clear the environment variable, to avoid affecting child
         * processes of this process. */
        pyi_unsetenv("PYINSTALLER_RESET_ENVIRONMENT");
    }
    free(env_var_value);

    /* Check if existing PyInstaller run-time environment exists, and
     * determine whether we should inherit it or not. This is done by
     * checking _PYI_ARCHIVE_FILE environment variable:
     *  - if it is not set, there is no environment to inherit. We will
     *    still reset all PyInstaller-related environment variables, in
     *    case whoever ran the process is trying to force the program to
     *    run as independent instance by having unset _PYI_ARCHIVE_FILE.
     *  - if it is set and the contents match our archive filename,
     *    we are using the same archive/executable as the parent process,
     *    and we should inherit its environment.
     *  - if it is set and the contents differ from our archive filename,
     *    then we are a different program from the parent process, and
     *    should reset the environment. */
    if (!reset_environment) {
        reset_environment = true;
        env_var_value = pyi_getenv("_PYI_ARCHIVE_FILE");
        if (env_var_value) {
            PYI_DEBUG("LOADER: _PYI_ARCHIVE_FILE already defined: %s\n", env_var_value);
            if (strcmp(pyi_ctx->archive_filename, env_var_value) == 0) {
                PYI_DEBUG("LOADER: using same archive file as parent environment!\n");
                reset_environment = false;
            } else {
                PYI_DEBUG("LOADER: using different archive file than parent environment!\n");
            }
        } else {
            PYI_DEBUG("LOADER: _PYI_ARCHIVE_FILE not defined...\n");
        }
        free(env_var_value);
    }

    /* Perform the actual environment reset, if necessary */
    if (reset_environment) {
        /* Set the _PYI_ARCHIVE_FILE */
        pyi_setenv("_PYI_ARCHIVE_FILE", pyi_ctx->archive_filename);

        /* Clear PyInstaller environment variables */
        pyi_unsetenv("_PYI_APPLICATION_HOME_DIR");

        pyi_unsetenv("_PYI_PARENT_PROCESS_LEVEL");

        pyi_unsetenv("_PYI_SPLASH_IPC");

#if defined(__linux__)
        pyi_unsetenv("_PYI_LINUX_PROCESS_NAME"); /* Linux only */
#endif
    }

    /* Use _PYI_PARENT_PROCESS_LEVEL environment variable to infer the
     * level (type) of this process:
     *  - parent (launcher) process
     *  - main (application) process
     *  - subprocess spawned from main application process. */
    env_var_value = pyi_getenv("_PYI_PARENT_PROCESS_LEVEL");
    if (!env_var_value || !env_var_value[0]) {
        /* We are either parent/launcher process of a onefile application,
         * or main/application process of a onedir application.
         *
         * On POSIX systems other than macOS, our onedir executables
         * restart ourselves after setting library search path; we mark
         * the main process before restart as parent/launcher, in order
         * to handle restart in `_pyi_main_handle_posix_onedir`. */
        if (pyi_ctx->is_onefile) {
            pyi_ctx->process_level = PYI_PROCESS_LEVEL_PARENT;
        } else {
#if defined(_WIN32) || defined(__APPLE__)
            /* Windows, macOS - mark as main process. */
            pyi_ctx->process_level = PYI_PROCESS_LEVEL_MAIN;
#elif defined(__CYGWIN__)
            /* Cygwin - mark as main process, as we do not need to restart.
             * For explanation, see comments in Cygwin-specific part where
             * library search path is set (further down this function). */
            pyi_ctx->process_level = PYI_PROCESS_LEVEL_MAIN;
#else
            /* Other POSIX systems - mark as parent/launcher due to having
             * to restart the process, as per comment block above. */
            pyi_ctx->process_level = PYI_PROCESS_LEVEL_PARENT;
#endif
        }
    } else if (strcmp(env_var_value, "0") == 0) {
        /* We are main application process of a onefile application,
         * or main application process of a onedir application after
         * restart (POSIX systems other than macOS). */
        pyi_ctx->process_level = PYI_PROCESS_LEVEL_MAIN;
    } else if (strcmp(env_var_value, "1") == 0) {
        /* We are a sub-process spawned from the main application process,
         * using the same executable (e.g., via sys.executable). */
        pyi_ctx->process_level = PYI_PROCESS_LEVEL_SUBPROCESS;
    } else {
        PYI_ERROR("Invalid value in _PYI_PARENT_PROCESS_LEVEL: %s\n", env_var_value);
        return -1;
    }
    free(env_var_value);

    PYI_DEBUG("LOADER: process level = %d\n", pyi_ctx->process_level);

    /* Store our process level in _PYI_PARENT_PROCESS_LEVEL for potential
     * child processes. If we are already in a spawned child sub-process,
     * leave the environment variable unchanged, as we do not keep track
     * of levels beyond that. */
    if (pyi_ctx->process_level < PYI_PROCESS_LEVEL_SUBPROCESS) {
        pyi_setenv("_PYI_PARENT_PROCESS_LEVEL", pyi_ctx->process_level == PYI_PROCESS_LEVEL_PARENT ? "0" : "1");
    }

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
    env_var_value = pyi_getenv("PYINSTALLER_STRICT_UNPACK_MODE"); /* strdup'd copy or NULL */
    if (env_var_value) {
        pyi_ctx->strict_unpack_mode = strcmp(env_var_value, "0") != 0;
    }
    free(env_var_value);

    /* On Linux, restore process name (passed from parent process via
     * environment variable. */
#if defined(__linux__)
    env_var_value = pyi_getenv("_PYI_LINUX_PROCESS_NAME");
    if (env_var_value) {
        PYI_DEBUG("LOADER: restoring process name: %s\n", env_var_value);
        prctl(PR_SET_NAME, env_var_value, 0, 0); /* Ignore failures */
    }
    free(env_var_value);
#endif  /* defined(__linux__) */

    /* Infer the process type (onefile parent, onefile child, onedir),
     * and based on that, determine the application's top-level directory. */
    if (pyi_ctx->is_onefile) {
        if (pyi_ctx->process_level == PYI_PROCESS_LEVEL_PARENT) {
            /* Parent process of onefile application; we need to unpack
             * into ephemeral application top-level directory. */
            PYI_DEBUG("LOADER: this is parent process of onefile application.\n");

            /* On Windows, initialize security descriptor for temporary
             * directory. This is required by `CreateDirectoryW()` calls
             * made when creating application's temporary directory and
             * its sub-directories during file extration. */
#if defined(_WIN32)
            PYI_DEBUG("LOADER: initializing security descriptor for temporary directory...\n");
            pyi_ctx->security_attr = pyi_win32_initialize_security_descriptor();
            if (pyi_ctx->security_attr == NULL) {
                PYI_ERROR("Failed to initialize security descriptor for temporary directory!\n");
                return -1;
            }
#endif

            /* Create temporary directory */
            PYI_DEBUG("LOADER: creating temporary directory (runtime_tmpdir=%s)...\n", pyi_ctx->runtime_tmpdir);

            if (pyi_create_temporary_application_directory(pyi_ctx) < 0) {
                PYI_ERROR("Could not create temporary directory!\n");
                return -1;
            }

            PYI_DEBUG("LOADER: created temporary directory: %s\n", pyi_ctx->application_home_dir);
        } else {
            /* Child process; the path to ephemeral application top-level
             * directory should be available in _PYI_APPLICATION_HOME_DIR
             * environment variable. */
            PYI_DEBUG(
                "LOADER: this is child process of onefile application (%s).\n",
                pyi_ctx->process_level == PYI_PROCESS_LEVEL_MAIN ?
                "main application process" : "spawned subprocess"
            );

            env_var_value = pyi_getenv("_PYI_APPLICATION_HOME_DIR");
            if (!env_var_value || !env_var_value[0]) {
                PYI_ERROR("_PYI_APPLICATION_HOME_DIR not set for onefile child process!\n");
                return -1;
            }

            /* Copy the application's top-level directory from environment */
            if (snprintf(pyi_ctx->application_home_dir, PYI_PATH_MAX, "%s", env_var_value) >= PYI_PATH_MAX) {
                PYI_ERROR("Path exceeds PYI_PATH_MAX limit.\n");
                free(env_var_value);
                return -1;
            }

            free(env_var_value);
        }
    } else {
        char executable_dir[PYI_PATH_MAX];
        bool is_macos_app_bundle = false;
#if defined(__APPLE__)
        size_t executable_dir_len;
#endif

        /* Determine application's top-level directory based on the
         * executable's location. */
        pyi_path_dirname(executable_dir, pyi_ctx->executable_filename);

#if defined(__APPLE__)
        executable_dir_len = strnlen(executable_dir, PYI_PATH_MAX);
        is_macos_app_bundle = executable_dir_len > 19 && strncmp(executable_dir + executable_dir_len - 19, ".app/Contents/MacOS", 19) == 0;
#endif

        if (is_macos_app_bundle) {
            /* macOS .app bundle; relocate top-level application directory
             * from Contents/MacOS directory to Contents/Frameworks */
            char contents_dir[PYI_PATH_MAX]; /* the parent Contents directory */
            pyi_path_dirname(contents_dir, executable_dir);
            pyi_path_join(pyi_ctx->application_home_dir, contents_dir, "Frameworks");
        } else {
            if (pyi_ctx->contents_subdirectory) {
                pyi_path_join(pyi_ctx->application_home_dir, executable_dir, pyi_ctx->contents_subdirectory);
            } else {
                snprintf(pyi_ctx->application_home_dir, PYI_PATH_MAX, "%s", executable_dir);
            }
        }

        /* Special handling for onedir mode on POSIX systems other than
         * macOS. To achieve single-process onedir mode, we need to set
         * library search path and restart the current process. This is
         * handled by the following helper function.
         * NOTE: under Cygwin, we do not have to restart the process to
         * set the search path, so skip this call.
         */
#if !defined(_WIN32) && !defined(__APPLE__) && !defined(__CYGWIN__)
        if (_pyi_main_handle_posix_onedir(pyi_ctx) < 0) {
            return -1;
        }
#endif
    }

    PYI_DEBUG("LOADER: application's top-level directory: %s\n", pyi_ctx->application_home_dir);

    /* In onefile parent process on Windows, attempt to pre-emptively
     * load system copies of VC runtime DLLs (e.g., VCRUNTIME140.dll
     * and VCRUNTIME140_1.dll). The bootloader itself has no need for
     * these DLLs - when building bootloader with MSVC, we statically
     * link both the CRT and VC runtime into the bootloader executable
     * (which allows the onefile executable to be launched on systems
     * without VC redistributable installed and without having to place
     * the VC runtime DLLs next to the executable). However, we need to
     * prevent the bundled copies from application's temporary directory
     * (which are used for example by python shared library loaded in
     * the *child* process of onefile build) from being loaded into this
     * process, because we might end up being unable to unload them and
     * thus remove the files during the cleanup..
     *
     * This issue seems to be caused by the OS, an anti-virus program,
     * or a 3rd party component injecting additional DLLs into our
     * process, and those additional DLLs depending on the VC runtime.
     * Initially, this seemed to affect only builds with splash screen
     * (see the follow-up discussion under #7106), because we need to
     * load Tcl/Tk DLLs, and those depend on the VC runtime; since we
     * unload Tcl/Tk DLLs during splash screen teardown, we free the
     * references on the VC runtime, and are usually able to also unload
     * VC runtime DLLs. This is not the case, however, if the VC runtime
     * DLLs remain locked due to injection of other 3rd party DLLs.
     * #9075 has shown that injection of 3rd party DLLs and subsequent
     * locking of VC runtime DLLs can also happen without splash screen,
     * so we now perform this pre-load in all onefile parent processes. */
#if defined(_WIN32)
    if (pyi_ctx->is_onefile && pyi_ctx->process_level == PYI_PROCESS_LEVEL_PARENT) {
        const wchar_t *dll_names[] = {
            L"VCRUNTIME140.dll",
            L"VCRUNTIME140_1.dll"
        };
        int i;

        /* Avoid accidentally picking up the DLLs from another
         * (instance of) frozen application that might have launched
         * this instance. I.e., call SetDllDirectoryW(NULL) to reset
         * the search path modification that happens in the code block
         * that follows this one (and is inherited by child processes). */
        SetDllDirectoryW(NULL);

        for (i = 0; i < sizeof(dll_names) / sizeof(dll_names[0]); i++) {
            const wchar_t *dll_name = dll_names[i];

            PYI_DEBUG_W(L"LOADER: attempting to pre-load system copy of %ls...\n", dll_name);
            if (LoadLibraryExW(dll_name, NULL, LOAD_LIBRARY_SEARCH_DEFAULT_DIRS)) {
                PYI_DEBUG_W(L"LOADER: successfully loaded system copy of %ls.\n", dll_name);
            } else {
                PYI_DEBUG_W(L"LOADER: could not load system copy of %ls.\n", dll_name);
            }
        }
    }
#endif /* defined(_WIN32) */

    /* On Windows and under Cygwin, add application's top-level directory
     * to DLL search path. Do so before we start loading bundled DLLs
     * (i.e., trying to start the splash screen). */
#if defined(_WIN32)
    if (1) {
        /* Windows - call SetDllDirectoryW() */
        wchar_t dllpath_w[PYI_PATH_MAX];
        if (pyi_win32_utf8_to_wcs(pyi_ctx->application_home_dir, dllpath_w, PYI_PATH_MAX) == NULL) {
            PYI_ERROR("Failed to convert DLL search path!\n");
            return -1;
        }
        PYI_DEBUG_W(L"LOADER: calling SetDllDirectoryW: %ls\n", dllpath_w);
        SetDllDirectoryW(dllpath_w);
    }
#elif defined(__CYGWIN__)
    if (1) {
        /* Under Cygwin, `dlopen()` uses `LD_LIBRARY_PATH` environment
         * variable for library names that do not include path to the
         * library file. However, linked libraries are resolved using
         * Windows' loader, which is controlled by `SetDllDirectoryW()`.
         * Therefore, we need to modify the search path of both mechanisms.
         *
         * Failing to call `SetDllDirectoryW` results in dependencies
         * of python shared library not being resolved when running the
         * frozen application outside of the Cygwin environment.
         *
         * Failing to set `LD_LIBRARY_PATH` seems to cause segmentation
         * faults in worker processes when `multiprocessing` is used
         * (both inside and outside of the Cygwin environment). */
        wchar_t dllpath_w[PYI_PATH_MAX];
        bool modify_ld_library_path;

        /* Convert POSIX path (whose root is determined by location of
         * the cygwin1.dll) into (wide-char) Windows path that can be
         * passed to `SetDllDirectoryW`. */
        if (cygwin_conv_path(CCP_POSIX_TO_WIN_W | CCP_RELATIVE, pyi_ctx->application_home_dir, dllpath_w, PYI_PATH_MAX) != 0) {
            PYI_PERROR("cygwin_conv_path", "Failed to convert DLL search path!\n");
            return -1;
        }

        /* On Cygwin, we do not have PYI_DEBUG_W macro available; so
         * use %S format to try printing the wide-char string. We can
         * be fairly certain that compiler is not MSVC, so %S does mean
         * wide-char in this context; there might still be garbled text
         * if string contains Unicode characters, but we will take the
         * risk... */
        PYI_DEBUG("LOADER: calling SetDllDirectoryW: %S\n", dllpath_w);
        SetDllDirectoryW(dllpath_w);

        /* Modify `LD_LIBRARY_PATH`, but only if we are the parent process
         * of onefile application, or main process of onedir application.
         * Their child processes will inherit the environment variable,
         * and the attempt to modify it again would result in duplicated
         * entries (and clobbered `LD_LIBRARY_PATH_ORIG`). */
        modify_ld_library_path = (
            (pyi_ctx->is_onefile && pyi_ctx->process_level == PYI_PROCESS_LEVEL_PARENT) ||
            (!pyi_ctx->is_onefile && pyi_ctx->process_level == PYI_PROCESS_LEVEL_MAIN)
        );
        if (modify_ld_library_path) {
            if (pyi_utils_set_library_search_path(pyi_ctx->application_home_dir) < 0) {
                return -1;
            }
        }
    }
#endif  /* defined(_WIN32) || defined(__CYGWIN__) */

    /* Setup splash screen, if applicable */
    _pyi_main_setup_splash_screen(pyi_ctx);

    /* Split execution between onefile parent process vs. onefile child
     * process / onedir process. */
    if (pyi_ctx->is_onefile && pyi_ctx->process_level == PYI_PROCESS_LEVEL_PARENT) {
        /* Onefile parent */
        return _pyi_main_onefile_parent(pyi_ctx);
    } else {
        /* Onedir or onefile child */
        return _pyi_main_onedir_or_onefile_child(pyi_ctx);
    }
}

#if defined(LAUNCH_DEBUG)

static void
_pyi_main_dump_command_line_arguments(const struct PYI_CONTEXT *pyi_ctx)
{
    int i;
    for (i = 0; i < pyi_ctx->argc; i++) {
#if defined(_WIN32)
        PYI_DEBUG_W(L"LOADER: argv[%d]: %ls\n", i, pyi_ctx->argv_w[i]);
#else
        PYI_DEBUG("LOADER: argv[%d]: %s\n", i, pyi_ctx->argv[i]);
#endif
    }
}

#endif /* defined(LAUNCH_DEBUG) */

static void
_pyi_main_read_runtime_options(struct PYI_CONTEXT *pyi_ctx)
{
    const struct ARCHIVE *archive = pyi_ctx->archive;
    const struct TOC_ENTRY *toc_entry;

    for (toc_entry = archive->toc; toc_entry < archive->toc_end; toc_entry = pyi_archive_next_toc_entry(archive, toc_entry)) {
        if (toc_entry->typecode != ARCHIVE_ITEM_RUNTIME_OPTION) {
            continue;
        }

        /* NOTE: option names are constants, so we use hard-coded
         * lengths as well to avoid invoking strlen() on each
         * comparison. */

        /* pyi-python-flag <value>
         *
         * Used to pass information about flags that collected python
         * shared library was built with, which might for example affect
         * the layout of PyConfig structure.
         *
         * Currently recongized flags:
         * - Py_GIL_DISABLED
         *
         * Might be specified multiple times, for each such flag. */
        if (strncmp(toc_entry->name, "pyi-python-flag", 15) == 0) {
            const char *flag_name = toc_entry->name + 16;
            if (strncmp(flag_name, "Py_GIL_DISABLED", 15) == 0) {
                pyi_ctx->nogil_enabled = 1;
            }
            continue;
        }

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
 *                        Splash screen setup                         *
\**********************************************************************/
static void
_pyi_main_setup_splash_screen(struct PYI_CONTEXT *pyi_ctx)
{
    char *env_suppress_splash;
    bool suppressed = false;
    bool is_eligible = false;

    /* Check if splash screen is available at all, i.e., if PKG/CArchive
     * contains SPLASH entry. */
    if (!pyi_ctx->archive->toc_splash) {
        PYI_DEBUG("LOADER: splash screen is unavailable.\n");
        return;
    }

    /* Check if user requested splash screen to be suppressed by setting
     * the PYINSTALLER_SUPPRESS_SPLASH_SCREEN environment variable to 1 */
    env_suppress_splash = pyi_getenv("PYINSTALLER_SUPPRESS_SPLASH_SCREEN");
    if (env_suppress_splash) {
        suppressed = strcmp(env_suppress_splash, "1") == 0;
    }
    free(env_suppress_splash);

    if (suppressed) {
        PYI_DEBUG("LOADER: splash screen is explicitly suppressed via environment variable!\n");
        /* Let `pyi_splash` module know that splash screen is intentionally
         * suppressed, by setting _PYI_SPLASH_IPC to 0. */
        pyi_setenv("_PYI_SPLASH_IPC", "0");
        return;
    }

    /* Splash screen should also be gracefully suppressed in sub-processes
     * spawned by the main application process. */
    if (pyi_ctx->process_level >= PYI_PROCESS_LEVEL_SUBPROCESS) {
        PYI_DEBUG("LOADER: spawned subprocess -  suppressing splash screen...\n");
        pyi_setenv("_PYI_SPLASH_IPC", "0");
        return;
    }

    /* Splash screen should be set up by the parent process of a onefile
     * application, and in the main process of a onedir application. */
    is_eligible = (
        (pyi_ctx->is_onefile && pyi_ctx->process_level == PYI_PROCESS_LEVEL_PARENT) ||
        (!pyi_ctx->is_onefile && pyi_ctx->process_level == PYI_PROCESS_LEVEL_MAIN)
    );
    if (!is_eligible) {
        PYI_DEBUG("LOADER: process is not eligible for splash screen\n");
        return;
    }

    /* Load splash screen resources. */
    PYI_DEBUG("LOADER: loading splash screen resources...\n");
    pyi_ctx->splash = pyi_splash_context_new();
    if (pyi_splash_setup(pyi_ctx->splash, pyi_ctx) != 0) {
        PYI_WARNING("Failed to load splash screen resources!\n");
        goto cleanup;
    }

    /* Splash screen resources loaded; setup up splash screen */
    PYI_DEBUG("LOADER: setting up splash screen...\n");

    /* In onefile mode, we need to extract dependencies (shared
     * libraries, .tcl files, etc.) from PKG archive. */
    if (pyi_ctx->is_onefile) {
        PYI_DEBUG("LOADER: extracting splash screen dependencies...\n");
        if (pyi_splash_extract(pyi_ctx->splash, pyi_ctx) != 0) {
            PYI_WARNING("Failed to unpack splash screen dependencies from PKG archive!\n");
            goto cleanup;
        }
    }

    /* Load Tcl/Tk shared libraries */
    if (pyi_splash_load_shared_libaries(pyi_ctx->splash) != 0) {
        PYI_WARNING("Failed to load Tcl/Tk shared libraries for splash screen!\n");
        goto cleanup;
    }

    /* Finally, start the splash screen */
    if (pyi_splash_start(pyi_ctx->splash, pyi_ctx->executable_filename) != 0) {
        PYI_WARNING("Failed to start splash screen!\n");
        goto cleanup;
    }

    /* Done! */
    return;

cleanup:
    /* A part of setup failed; clean up the state by finalizing it, and
     * free the allocated structure. */
    pyi_splash_finalize(pyi_ctx->splash);
    pyi_splash_context_free(&pyi_ctx->splash);

    return;
}

/**********************************************************************\
 *                  Onedir or onefile child codepath                  *
\**********************************************************************/
static int
_pyi_main_onedir_or_onefile_child(struct PYI_CONTEXT *pyi_ctx)
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
            pyi_ctx->ae_ctx = pyi_apple_install_event_handlers(pyi_ctx);
            if (pyi_ctx->ae_ctx == NULL) {
                PYI_ERROR("Failed to install AppleEvent handlers!\n");
                return -1;
            }
            /* Process Apple events; this updates argc_pyi/argv_pyi
             * accordingly */
            pyi_apple_process_events(pyi_ctx->ae_ctx, 0.25);  /* short_timeout (250 ms) */
            /* Uninstall event handlers */
            pyi_apple_uninstall_event_handlers(&pyi_ctx->ae_ctx);
            /* The processing of Apple events swallows up the initial
             * activation event, whatever it might have been (typically
             * oapp, but could also be odoc or GURL if application is
             * launched in response to request to open file/URL).
             * This seems to cause issues with some UI frameworks
             * (Tcl/Tk, in particular); so we submit a new oapp event
             * to ourselves... */
            pyi_apple_submit_oapp_event();
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

    PYI_DEBUG("LOADER: end of process reached!\n");
    return ret;
}


/**********************************************************************\
 *                      Onefile parent codepath                       *
\**********************************************************************/
static int
_pyi_main_onefile_parent(struct PYI_CONTEXT *pyi_ctx)
{
    int ret;

    /* Extract files to temporary directory */
    PYI_DEBUG("LOADER: extracting files to temporary directory...\n");
    if (pyi_launch_extract_files_from_archive(pyi_ctx) < 0) {
        PYI_DEBUG("LOADER: failed to extract files!\n");
        return -1;
    }

    /* At this point, extraction to temporary directory is complete,
     * and we can free the Windows security descriptor that was used
     * during creation of temporary directory and its sub-directories. */
#if defined(_WIN32)
    pyi_win32_free_security_descriptor(&pyi_ctx->security_attr);
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
            PYI_DEBUG("LOADER: storing process name: %s\n", processname);
            pyi_setenv("_PYI_LINUX_PROCESS_NAME", processname);
        }
    }
#endif  /* defined(__linux__) */

    /* On OSes other than Windows and macOS, we need to set library
     * search path (via LD_LIBRARY_PATH or equivalent). Since the
     * search path cannot be modified for the running process, we
     * need to set it in the parent process, before launching the
     * child process. Skip this call under Cygwin, because it was
     * already made in the common codepath. */
#if !defined(_WIN32) && !defined(__APPLE__) && !defined(__CYGWIN__)
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
     *
     * NOTE: this step is now somewhat redundant in onefile builds,
     * because we use hidden window to capture and process events
     * related to session shutdown while we wait for child process to
     * exit. Creation of that hidden window and/or its message processing
     * would also hide the spinning wheel cursor. */
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
        TransformProcessType(&psn, kProcessTransformToBackgroundApplication);
    }
#endif

    /* Pass top-level application directory (the temporary directory
     * where files were extracted) to the child process via
     * corresponding environment variable. */
    PYI_DEBUG("LOADER: setting _PYI_APPLICATION_HOME_DIR to %s\n", pyi_ctx->application_home_dir);
    pyi_setenv("_PYI_APPLICATION_HOME_DIR", pyi_ctx->application_home_dir);

    /* Start the child process that will execute user's program. */
    PYI_DEBUG("LOADER: starting the child process...\n");
    ret = pyi_utils_create_child(pyi_ctx);

    PYI_DEBUG("LOADER: child process exited (return code: %d)\n", ret);

    PYI_DEBUG("LOADER: performing cleanup...\n");

    /* The cleanup code for onefile parent process is organized in a
     * helper function, so that on Windows, we can also call it from
     * session shutdown callback.
     *
     * If cleanup failed (and this is considered error; see the
     * implementation), modify the exit code. */
    if (pyi_main_onefile_parent_cleanup(pyi_ctx) < 0) {
        ret = -1;
    }

    /* Re-raise child's signal, if necessary (POSIX only) */
#ifndef _WIN32
    if (pyi_ctx->child_signalled) {
        PYI_DEBUG("LOADER: re-raising child signal %d\n", pyi_ctx->child_signal);
        raise(pyi_ctx->child_signal);
    }
#endif

    PYI_DEBUG("LOADER: end of process reached!\n");
    return ret;
}

/* This function must be visible to other compilation units, so that
 * on Windows, we can also call it from session shutdown callback. */
int pyi_main_onefile_parent_cleanup(struct PYI_CONTEXT *pyi_ctx)
{
    int cleanup_status;
    int ret = 0;

    /* Finalize splash screen before temp directory gets wiped, since the splash
     * screen might hold handles to shared libraries inside the temp dir. Those
     * wouldn't be removed, leaving the temp folder behind. */
    pyi_splash_finalize(pyi_ctx->splash);
    pyi_splash_context_free(&pyi_ctx->splash);

    /* Remove the application's temporary directory */
    PYI_DEBUG("LOADER: removing temporary directory: %s\n", pyi_ctx->application_home_dir);
    cleanup_status = pyi_recursive_rmdir(pyi_ctx->application_home_dir);

#ifdef _WIN32
    /* On Windows, we might fail to remove temporary directory due to
     * locked file(s), which might happen due to various reasons. Try
     * to mitigate (some of) them and attempt to remove the temporary
     * directory again. */
    if (cleanup_status < 0) {
        PYI_DEBUG_W(L"LOADER: failed to remove temporary directory - attempting to mitigate the situation...\n");
        cleanup_status = pyi_win32_mitigate_locked_temporary_directory(pyi_ctx);
        if (cleanup_status == 0) {
            PYI_DEBUG_W(L"LOADER: mitigation succeeded.\n");
        } else {
            PYI_DEBUG_W(L"LOADER: mitigation failed!\n");
        }
    }
#endif

    if (cleanup_status < 0) {
        /* Return error if we failed to remove temporary directory while
         * strict unpack mode is enabled. */
        if (pyi_ctx->strict_unpack_mode) {
            PYI_ERROR("Failed to remove temporary directory: %s\n", pyi_ctx->application_home_dir);
            ret = -1;
        } else {
            PYI_WARNING("Failed to remove temporary directory: %s\n", pyi_ctx->application_home_dir);
        }
    } else {
        PYI_DEBUG("LOADER: temporary directory %s was successfully removed.\n", pyi_ctx->application_home_dir);
    }

    /* Clean up the archive structure */
    pyi_archive_free(&pyi_ctx->archive);

    return ret;
}


/**********************************************************************\
 *                     Executable file resolution                     *
\**********************************************************************/
#ifdef _WIN32

static int
_pyi_resolve_executable_win32(char *executable_filename)
{
    wchar_t modulename_w[PYI_PATH_MAX];

    /* GetModuleFileNameW returns an absolute, fully qualified path */
    if (!GetModuleFileNameW(NULL, modulename_w, PYI_PATH_MAX)) {
        PYI_WINERROR_W(L"GetModuleFileNameW", L"Failed to obtain executable path.\n");
        return -1;
    }

    /* If path is a symbolic link, resolve it */
    if (pyi_win32_is_symlink(modulename_w)) {
        wchar_t executable_filename_w[PYI_PATH_MAX];
        int offset = 0;

        PYI_DEBUG_W(L"LOADER: executable file %ls is a symbolic link - resolving...\n", modulename_w);

        /* Resolve */
        if (pyi_win32_realpath(modulename_w, executable_filename_w) < 0) {
            PYI_ERROR_W(L"Failed to resolve full path to executable %ls.\n", modulename_w);
            return -1;
        }

        /* Remove the extended path indicator, to avoid potential issues due
         * to its appearance in `sys.executable`, `sys._MEIPASS`, etc. */
        if (wcsncmp(L"\\\\?\\", executable_filename_w, 4) == 0) {
            offset = 4;
        }

        /* Convert to UTF-8 */
        if (!pyi_win32_wcs_to_utf8(executable_filename_w + offset, executable_filename, PYI_PATH_MAX)) {
            PYI_ERROR_W(L"Failed to convert executable path to UTF-8.\n");
            return -1;
        }
    } else {
        /* Convert to UTF-8 */
        if (!pyi_win32_wcs_to_utf8(modulename_w, executable_filename, PYI_PATH_MAX)) {
            PYI_ERROR_W(L"Failed to convert executable path to UTF-8.\n");
            return -1;
        }
    }

    return 0;
}

#elif __APPLE__

static int
_pyi_resolve_executable_macos(char *executable_filename)
{
    char program_path[PYI_PATH_MAX];
    uint32_t name_length = sizeof(program_path);

    /* macOS has special function to obtain path to executable.
     * This may return a symbolic link. */
    if (_NSGetExecutablePath(program_path, &name_length) != 0) {
        PYI_ERROR("Failed to obtain executable path via _NSGetExecutablePath!\n");
        return -1;
    }

    /* Canonicalize the filename and resolve symbolic links */
    if (realpath(program_path, executable_filename) == NULL) {
        PYI_DEBUG("LOADER: failed to resolve full path for %s\n", program_path);
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
    char basename[PYI_PATH_MAX];
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
    char *search_paths = pyi_getenv("PATH"); /* returns a copy */
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
_pyi_resolve_executable_posix(const char *argv0, char *executable_filename, char *loader_filename)
{
    /* On Linux, Cygwin, FreeBSD, and Solaris, we try /proc entry first.
     * The entry points at "true" file location, i.e., fully canonicalized
     * and with all symbolic links resolved. */
    ssize_t name_len = -1;

#if defined(__linux__) || defined(__CYGWIN__)
    name_len = readlink("/proc/self/exe", executable_filename, PYI_PATH_MAX - 1);  /* Linux, Cygwin */
#elif defined(__FreeBSD__)
    name_len = readlink("/proc/curproc/file", executable_filename, PYI_PATH_MAX - 1);  /* FreeBSD */
#elif defined(__sun)
    name_len = readlink("/proc/self/path/a.out", executable_filename, PYI_PATH_MAX - 1);  /* Solaris */
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
        PYI_DEBUG("LOADER: resolved executable file %s is ld.so dynamic linker/loader - storing its name.\n", executable_filename);
        strncpy(loader_filename, executable_filename, PYI_PATH_MAX); /* both buffers are guaranteed to be PYI_PATH_MAX-sized */
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
        PYI_DEBUG("LOADER: resolving program path from argv[0]: %s\n", argv0);
        if (realpath(argv0, executable_filename) == NULL) {
            PYI_DEBUG("LOADER: failed to resolve full path for %s\n", argv0);
            return -1;
        }
    } else {
        /* No path, just program name. Search $PATH for executable with
         * matching name. */
        char program_path[PYI_PATH_MAX];

        if (_pyi_find_progam_in_search_path(argv0, program_path)) {
            /* Program found in $PATH; resolve full path */
            PYI_DEBUG("LOADER: program %s found in PATH: %s. Resolving full path...\n", argv0, program_path);
            if (realpath(program_path, executable_filename) == NULL) {
                PYI_DEBUG("LOADER: failed to resolve full path for %s\n", program_path);
                return -1;
            }
        } else {
            /* Searching $PATH failed; try resolving the name as-is,
             * and hope for the best. NOTE: can we even reach this part?
             * How was the executable even launched in such case? */
            PYI_DEBUG("LOADER: could not find %s in $PATH! Attempting to resolve as-is...\n", argv0);
            if (realpath(argv0, executable_filename) == NULL) {
                PYI_DEBUG("LOADER: failed to resolve full path for %s\n", argv0);
                return -1;
            }
        }
    }

    return 0;
}

#endif


static int
_pyi_main_resolve_executable(struct PYI_CONTEXT *pyi_ctx)
{
    /* Resolve using OS-specific implementation */
#ifdef _WIN32
    return _pyi_resolve_executable_win32(pyi_ctx->executable_filename);
#elif __APPLE__
    return _pyi_resolve_executable_macos(pyi_ctx->executable_filename);
#else
    return _pyi_resolve_executable_posix(pyi_ctx->argv[0], pyi_ctx->executable_filename, pyi_ctx->dynamic_loader_filename);
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
_pyi_main_resolve_pkg_archive(struct PYI_CONTEXT *pyi_ctx)
{
    int status;

    /* Try opening embedded archive first */
    PYI_DEBUG("LOADER: trying to load executable-embedded archive...\n");
    pyi_ctx->archive = pyi_archive_open(pyi_ctx->executable_filename);
    if (pyi_ctx->archive != NULL) {
        /* Copy executable filename to archive filename; we know it does not exceed PYI_PATH_MAX */
        snprintf(pyi_ctx->archive_filename, PYI_PATH_MAX, "%s", pyi_ctx->executable_filename);
        return 0;
    }

    PYI_DEBUG("LOADER: failed to open executable-embedded archive!\n");

    /* Check if side-load is allowed */
    status = _pyi_allow_pkg_sideload(pyi_ctx->executable_filename);
    if (status != 0) {
        PYI_DEBUG("LOADER: side-load is disabled (code %d)!\n", status);
        PYI_ERROR(
            "Could not load PyInstaller's embedded PKG archive from the executable (%s)\n",
            pyi_ctx->executable_filename
        );
        return -1;
    }

    /* Infer the archive filename in side-load mode. On Windows, the .exe
     * suffix is replaced with .pkg, while elsewhere, .pkg suffix is
     * appended to the executable file name. */
#ifdef _WIN32
    snprintf(pyi_ctx->archive_filename, PYI_PATH_MAX, "%s", pyi_ctx->executable_filename);
    strcpy(pyi_ctx->archive_filename + strlen(pyi_ctx->archive_filename) - 3, "pkg");
#else
    if (snprintf(pyi_ctx->archive_filename, PYI_PATH_MAX, "%s.pkg", pyi_ctx->executable_filename) >= PYI_PATH_MAX) {
        return -1;
    }
#endif

    PYI_DEBUG("LOADER: trying to load external PKG archive (%s)...\n", pyi_ctx->archive_filename);

    pyi_ctx->archive = pyi_archive_open(pyi_ctx->archive_filename);
    if (pyi_ctx->archive == NULL) {
        PYI_ERROR(
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
#if !defined(_WIN32) && !defined(__APPLE__) && !defined(__CYGWIN__)

/* On POSIX systems, we cannot dynamically set library search path for
 * the running process. On OSes other than macOS (where we solve this
 * by rewriting library paths in collected binaries), we therefore
 * achieve single-process onedir mode by setting the search-path
 * environment variable (i.e., `LD_LIBRARY_PATH`) and then restart/replace
 * the current process via `exec()` without `fork()` for the environment
 * changes (library search path) to take effect. We use a special
 * environment variable to keep track of whether the process has already
 * been restarted or not.
 *
 * NOTE: this function is not used on Cygwin, where `LD_LIBRARY_PATH`
 * is used only to resolve shared libraries opened by `dlopen()` (without
 * full path), while linked libraries are resolved by the DLL search
 * path set by `SetDllDirectoryW()`. Therefore, we can just set the
 * environment variable without restarting the process, which we handle
 * directly in the main program codepath. */
static int
_pyi_main_handle_posix_onedir(struct PYI_CONTEXT *pyi_ctx)
{
    /* Check if we need to restart */
    if (pyi_ctx->process_level > PYI_PROCESS_LEVEL_PARENT) {
        PYI_DEBUG("LOADER: POSIX onedir process has already restarted itself (level = %d).\n", pyi_ctx->process_level);
        return 0;
    }

    PYI_DEBUG("LOADER: POSIX onedir process needs to set library search path and restart itself.\n");

    /* Set up the library search path (by modifying LD_LIBRARY_PATH or
     * equivalent), so that the restarted process will be able to find
     * the collected libraries in the top-level application directory. */
    if (pyi_utils_set_library_search_path(pyi_ctx->application_home_dir) < 0) {
        return -1;
    }

    /* Restart the process, by calling execvp() without fork(). */
    /* NOTE: the codepath that ended up here does not perform any
     * argument modification, so we always use pyi_ctx->argv (as
     * pyi_ctx->pyi_argv is unavailable). */
    if (pyi_ctx->dynamic_loader_filename[0] != 0) {
        char *const *exec_argv;

        PYI_DEBUG("LOADER: restarting process via execvp and dynamic linker/loader: %s\n", pyi_ctx->dynamic_loader_filename);
        exec_argv = pyi_prepend_dynamic_loader_to_argv(pyi_ctx->argc, pyi_ctx->argv, pyi_ctx->dynamic_loader_filename);
        if (exec_argv == NULL) {
            PYI_ERROR("LOADER: failed to allocate argv array for execvp!\n");
            return -1;
        }
        if (execvp(pyi_ctx->dynamic_loader_filename, exec_argv) < 0) {
            PYI_ERROR("LOADER: failed to restart process: %s\n", strerror(errno));
            return -1;
        }
    } else {
        PYI_DEBUG("LOADER: restarting process via execvp\n");
        if (execvp(pyi_ctx->executable_filename, pyi_ctx->argv) < 0) {
            PYI_ERROR("LOADER: failed to restart process: %s\n", strerror(errno));
            return -1;
        }
    }

    /* Unreachable */
    return 0;
}

#endif
