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

#ifdef _WIN32
    #include <windows.h>
#else
    #include <dlfcn.h> /* dlerror */
#endif
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* PyInstaller headers */
#include "pyi_global.h"
#include "pyi_archive.h"
#include "pyi_main.h"
#include "pyi_utils.h"
#include "pyi_path.h"
#include "pyi_splash.h"

/**
 * Splash Screen Feature
 *
 * A splash screen is a graphical window in which a program-defined screen
 * is displayed. It is normally used to give the user visual feedback,
 * indicating that the program has been started.
 *
 * In this file the splash screen feature as of discussed in pyinstaller#4354 is
 * implemented. To show a splash screen the Tk library is used. Tk is accessed by
 * and distributed with Tcl inside the python standard library (as of python 3.8
 * with Tcl/Tk 8.6). Python uses Tcl/Tk in the tkinter module. Tkinter is a wrapper
 * between python and Tcl, so using tkinter will use Tcl/Tk. Because tkinter is
 * distributed with any common python installation and it is cross-platform,
 * it is also used for this splash screen.
 *
 * If splash screen is enabled, PyInstaller bundles all necessary Tcl/Tk resources
 * for inclusion in the frozen application. This results in a slightly bigger
 * application distribution if a splash screen is used, but it is assumed to be negligible.
 *
 * Tcl is a simple high-level programming language like python. It is often embedded into
 * C application for prototyping. Together with Tk (called Tcl/Tk) it is a very powerful
 * tool to build graphical user interfaces and is often used to give C applications
 * a GUI, since it is easy to embed.
 *
 * The implementation of splash screen looks for splash screen resources in the frozen
 * application's archive; if found, it dynamically loads the Tcl and Tk shared libraries,
 * initializes a minimal Tcl/Tk environment, and runs the splash screen in it.
 *
 * Only threaded Tcl is supported; i.e., Tcl had to be compiled with the --enable-threads
 * flag, which is it by default on Windows and macOS. Many Linux distributions also come
 * with threaded Tcl installation, although it is not guaranteed. PyInstaller checks at
 * build time if Tcl is threaded and raises an error if it is not.
 */


/* Forward declarations */
static Tcl_ThreadCreateProc _splash_init;
struct Splash_Event;


/*
 * Initialize the splash screen context by reading its data and defining
 * the necessary paths and resources.
 */
int
pyi_splash_setup(struct SPLASH_CONTEXT *splash, const struct PYI_CONTEXT *pyi_ctx)
{
    struct SPLASH_DATA_HEADER *data_header;

    /* Read splash resources entry from the archive */
    data_header = (struct SPLASH_DATA_HEADER *)pyi_archive_extract(pyi_ctx->archive, pyi_ctx->archive->toc_splash);
    if (data_header == NULL) {
        return -1; /* Failed to read splash resources */
    }

    /* In onedir mode, Tcl/Tk dependencies (shared libraries, .tcl files)
     * are located directly in top-level application directory. In onefile
     * mode, they are extracted into temporary/ephemeral top-level
     * application directory.
     *
     * NOTE: the name fields in SPLASH_DATA_HEADER have fixed width (32
     * or 16 characters), and are *implicitly* NUL terminated; the build
     * process uses zero padding and is ensuring that strings themselves
     * have no more than N-1 characters long. */

    /* Tcl shared library */
    if (pyi_path_join(splash->tcl_libpath, pyi_ctx->application_home_dir, data_header->tcl_libname) == NULL) {
        PYI_WARNING("SPLASH: length of Tcl shared library path exceeds maximum path length!\n");
        free(data_header);
        return -1;
    }

    /* Tk shared library */
    if (pyi_path_join(splash->tk_libpath, pyi_ctx->application_home_dir, data_header->tk_libname) == NULL) {
        PYI_WARNING("SPLASH: length of Tk shared library path exceeds maximum path length!\n");
        free(data_header);
        return -1;
    }

    /* Tk modules directory */
    if (pyi_path_join(splash->tk_lib, pyi_ctx->application_home_dir, data_header->tk_lib) == NULL) {
        PYI_WARNING("SPLASH: length of Tk shared library path exceeds maximum path length!\n");
        free(data_header);
        return -1;
    }

    /* Copy the script into a buffer owned by SPLASH_STATUS */
    splash->script_len = pyi_be32toh(data_header->script_len);
    splash->script = (char *)calloc(1, splash->script_len + 1);

    /* Copy the image into a buffer owned by SPLASH_STATUS */
    splash->image_len = pyi_be32toh(data_header->image_len);
    splash->image = (char *)malloc(splash->image_len);

    /* Copy the requirements array into a buffer owned by SPLASH_STATUS */
    splash->requirements_len = pyi_be32toh(data_header->requirements_len);
    splash->requirements = (char *)malloc(splash->requirements_len);

    if (splash->script == NULL || splash->image == NULL || splash->requirements == NULL) {
        PYI_ERROR("Could not allocate memory for splash screen resources.\n");
        free(data_header);
        return -1;
    }

    /* Copy the data into their respective fields */
    memcpy(
        splash->script,
        ((char *)data_header) + pyi_be32toh(data_header->script_offset),
        splash->script_len
    );
    memcpy(
        splash->image,
        ((char *)data_header) + pyi_be32toh(data_header->image_offset),
        splash->image_len
    );
    memcpy(
        splash->requirements,
        ((char *)data_header) + pyi_be32toh(data_header->requirements_offset),
        splash->requirements_len
    );

    /* Free raw header data */
    free(data_header);

    return 0;
}

/*
 * Start the splash screen.
 *
 * As this uses bound functions from Tcl/Tk shared libraries, it must
 * be called after the shared libaries have been loaded and their
 * symbols bound.
 *
 * The splash screen needs to run in a separate thread, otherwise
 * the event loop of the GUI would block the extraction. We only
 * implement this for threaded tcl, since many threading functions
 * from tcl are only available, if tcl was compiled with threading
 * support.
 *
 * In order to start the splash screen a new thread is created, in which
 * the internal function _splash_init is called. This function will setup
 * the environment for the splash screen.
 *
 * If the thread was created successfully, the return value will be 0,
 * otherwise a non zero number is returned. Note that a return code of
 * 0 does not necessarily mean, that Tcl/Tk was successfully initialized.
 */
int
pyi_splash_start(struct SPLASH_CONTEXT *splash, const char *executable)
{
    const struct DYLIB_TCLTK *dylib_tcltk = splash->dylib_tcltk;

    /* Make sure shared libraries have been loaded and their symbols
     * bound. */
    if (!dylib_tcltk) {
        return -1;
    }

    dylib_tcltk->Tcl_MutexLock(&splash->context_mutex);

    /* This functions needs to be called before everything else is done
     * with Tcl, otherwise the behavior of Tcl is undefined. */
    dylib_tcltk->Tcl_FindExecutable(executable);

    /* At the time of writing, Tcl on Windows does not support joinable
     * threads. As per https://www.tcl.tk/man/tcl/TclLib/Thread.htm:
     * "Windows currently does not support joinable threads. This flag
     * value is therefore ignored on this platform."
     * The same page further states "Trying to wait for the exit of a
     * non-joinable thread or a thread which is already waited upon will
     * result in an error." but trying to call Tcl_JoinThread() on windows
     * seems to block forever. For now, disable joinable threads on
     * Windows, and if https://github.com/tcltk/tcl/tree/windows-thread-join
     * gets merged, implement version-based check. */
#if defined(_WIN32)
    splash->thread_joinable = false;
#else
    splash->thread_joinable = true;
#endif

    /* We try to create a new thread (in which the Tcl interpreter will run) with
     * methods provided by Tcl. This function will return TCL_ERROR if it is
     * either not implemented (Tcl is not threaded) or an error occurs.
     * Since we only support threaded Tcl, the error is fatal. */
    if (dylib_tcltk->Tcl_CreateThread(
        &splash->thread_id, /* location to store thread ID */
        _splash_init, /* procedure/function to run in the new thread */
        splash, /* parameters to pass to procedure */
        0, /* use default stack size */
        splash->thread_joinable ? TCL_THREAD_JOINABLE : TCL_THREAD_NOFLAGS /* flags */
    ) != TCL_OK) {
        PYI_ERROR("SPLASH: Tcl is not threaded. Only threaded Tcl is supported.\n");
        dylib_tcltk->Tcl_MutexUnlock(&splash->context_mutex);
        pyi_splash_finalize(splash);
        return -1;
    }
    dylib_tcltk->Tcl_MutexLock(&splash->start_mutex);
    dylib_tcltk->Tcl_MutexUnlock(&splash->context_mutex);

    PYI_DEBUG("SPLASH: created thread for Tcl interpreter.\n");

    /* To avoid a race condition between the Tcl and python interpreter
     * we need to wait until the splash screen has been started. We lock
     * here until the Tcl thread notified us that it has finished starting up.
     * This is necessary to ensure that the `_PYI_SPLASH_IPC` environment
     * variable that is set by the Tcl splash screen script is always
     * propagated into python's `os.environ`, which reflects the state
     * of environment when python interpreter is initialized. */
    dylib_tcltk->Tcl_ConditionWait(&splash->start_cond, &splash->start_mutex, NULL);
    dylib_tcltk->Tcl_MutexUnlock(&splash->start_mutex);
    dylib_tcltk->Tcl_ConditionFinalize(&splash->start_cond);
    PYI_DEBUG("SPLASH: splash screen started.\n");

    return 0;
}

/*
 * Extract the necessary parts of the splash screen resources from
 * the PKG/CArchive, if they are bundled (i.e., onefile mode). No-op
 * in onedir mode.
 *
 * The files are extracted into (temporary) application's top-level
 * directory; later, when `pyi_launch_extract_files_from_archive`
 * performs the main extraction, it skips the extraction of files that
 * were already extracted here (and exempts them from warning message).
 */
int
pyi_splash_extract(struct SPLASH_CONTEXT *splash, const struct PYI_CONTEXT *pyi_ctx)
{
    const struct ARCHIVE *archive = pyi_ctx->archive;
    const struct TOC_ENTRY *toc_entry;
    const char *requirement_filename = NULL;
    char output_filename[PYI_PATH_MAX];
    size_t pos;

    /* No-op in onedir mode */
    if (!pyi_ctx->is_onefile) {
        return 0;
    }

    /* Iterate over the requirements array */
    for (pos = 0; pos < (size_t)splash->requirements_len; pos += strlen(requirement_filename) + 1) {
        /* Read filename from requirements array */
        requirement_filename = splash->requirements + pos;

        /* Look-up entry in archive's TOC */
        toc_entry = pyi_archive_find_entry_by_name(archive, requirement_filename);
        if (toc_entry == NULL) {
            PYI_ERROR("SPLASH: could not find requirement %s in archive.\n", requirement_filename);
            return -1;
        }

        /* Construct output filename */
        if (snprintf(output_filename, PYI_PATH_MAX, "%s%c%s", pyi_ctx->application_home_dir, PYI_SEP, requirement_filename) >= PYI_PATH_MAX) {
            PYI_ERROR("SPLASH: extraction path length exceeds maximum path length!\n");
            return -1;
        }

        /* Check if file already exists (it should not) */
        if (pyi_path_exists(output_filename) == 1) {
            if (pyi_ctx->strict_unpack_mode) {
                PYI_ERROR("SPLASH: file already exists but should not: %s\n", output_filename);
                return -1;
            } else {
                PYI_WARNING("SPLASH: file already exists but should not: %s\n", output_filename);
            }
        }

        /* Create parent directory tree */
        if (pyi_create_parent_directory_tree(pyi_ctx, pyi_ctx->application_home_dir, requirement_filename) < 0) {
            PYI_ERROR("SPLASH: failed to create parent directory structure.\n");
            return -1;
        }

        /* Extract file into the splash dependencies directory */
        if (pyi_archive_extract2fs(archive, toc_entry, output_filename)) {
            PYI_ERROR("SPLASH: could not extract requirement %s.\n", toc_entry->name);
            return -2;
        }
    }

    return 0;
}

/* Check if the given TOC entry is a splash dependency. Used by
 * `pyi_launch_extract_files_from_archive` to avoid overwriting files
 * that were already extracted by `pyi_splash_extract` (and are in use
 * by splash screen code).
 */
int
pyi_splash_is_splash_requirement(struct SPLASH_CONTEXT *splash, const char *name)
{
    const char *requirement_filename = NULL;
    size_t pos;

    /* Iterate over the requirements array */
    for (pos = 0; pos < (size_t)splash->requirements_len; pos += strlen(requirement_filename) + 1) {
        /* Read filename from requirements array */
        requirement_filename = splash->requirements + pos;

#if defined(_WIN32) || defined(__APPLE__)
        /* On Windows and macOS, use case-insensitive comparison to
         * simulate case-insensitive filesystem for extractable entries. */
        if (strcasecmp(requirement_filename, name) == 0) {
            return 1;
        }
#else
        if (strcmp(requirement_filename, name) == 0) {
            return 1;
        }
#endif
    }

    return 0;
}


/* Load Tcl/Tk shared libraries and bind required symbols (functions). */
int
pyi_splash_load_shared_libaries(struct SPLASH_CONTEXT *splash)
{
    PYI_DEBUG("SPLASH: loading Tcl library from: %s\n", splash->tcl_libpath);
    PYI_DEBUG("SPLASH: loading Tk library from: %s\n", splash->tk_libpath);

    /* Load shared libraries and bind symbols */
    splash->dylib_tcltk = pyi_dylib_tcltk_load(splash->tcl_libpath, splash->tk_libpath);
    if (splash->dylib_tcltk == NULL) {
        PYI_ERROR("SPLASH: failed to load Tcl/Tk shared libraries!\n");
        return -1;
    }

    return 0;
}

/*
 * Finalizes the splash screen.
 */
int
pyi_splash_finalize(struct SPLASH_CONTEXT *splash)
{
    const struct DYLIB_TCLTK *dylib_tcltk;

    if (splash == NULL) {
        return 0;
    }

    /* If we failed to fully attach Tcl/Tk libraries (either because one
     * of the libraries failed to load, or because we failed to load one
     * of the symbols from the libraries), there is nothing left to do. */
    dylib_tcltk = splash->dylib_tcltk;
    if (!dylib_tcltk) {
        return 0;
    }

    PYI_DEBUG("SPLASH: cleaning up splash screen resources...\n");

    /* Ensure this block is completely executed either before cleanup
     * code in _splash_init (in which case, splash->interp is still
     * non-NULL, and we wait for splash screen thread to signal its
     * exit) or after it (in which case, splash->interp is NULL, and
     * we can skip this part). */
    dylib_tcltk->Tcl_MutexLock(&splash->exit_mutex);
    if (splash->interp != NULL) {
        PYI_DEBUG("SPLASH: splash screen thread still running; signalling it to shut down...\n");

        /* If the Tcl thread still exists, we notify it and wait for it
         * to exit. */
        splash->exit_main_loop = true;

        /* We need to post a fake event into the event queue in order
         * to unblock Tcl_DoOneEvent, so the Tcl main loop can exit. */
        pyi_splash_send(splash, true, NULL, NULL);
        dylib_tcltk->Tcl_ConditionWait(&splash->exit_wait, &splash->exit_mutex, NULL);
        dylib_tcltk->Tcl_MutexUnlock(&splash->exit_mutex);
        dylib_tcltk->Tcl_ConditionFinalize(&splash->exit_wait);

        PYI_DEBUG("SPLASH: splash screen thread has shut down.\n");
    } else {
        dylib_tcltk->Tcl_MutexUnlock(&splash->exit_mutex);
        PYI_DEBUG("SPLASH: splash screen thread has already shut down.\n");
    }

    /* Join the splash screen thread, to ensure it is fully finished */
    if (splash->thread_joinable && splash->thread_id) {
        int ret;
        PYI_DEBUG("SPLASH: joining the splash screen thread...\n");
        ret = dylib_tcltk->Tcl_JoinThread(splash->thread_id, NULL); /* We do not need thread's return code */
        PYI_DEBUG("SPLASH: splash screen thread join %s\n", ret == TCL_OK ? "succeeded." : "failed!");
        /* ret is used only in debug messages; suppress variable-set-but-unused
         * gcc warning in non-debug build */
        (void)ret;
    }

    /* Cleanup mutexes */
    dylib_tcltk->Tcl_MutexFinalize(&splash->context_mutex);
    dylib_tcltk->Tcl_MutexFinalize(&splash->call_mutex);
    dylib_tcltk->Tcl_MutexFinalize(&splash->start_mutex);
    dylib_tcltk->Tcl_MutexFinalize(&splash->exit_mutex);

    /* This function should only be called after python has been
     * destroyed with Py_Finalize. Tcl/Tk/tkinter do **not** support
     * multiple instances of themselves due to restrictions of Tcl
     * (for reference see _tkinter PyMethodDef m_size field or
     * disabled registration of Tcl_Finalize inside _tkinter.c)
     * The python program may have imported tkinter, which keeps
     * its own tcl interpreter. If we finalized Tcl here, the
     * Tcl interpreter of tkinter would also be finalized, resulting
     * in a weird state of tkinter. */
    dylib_tcltk->Tcl_Finalize();

    PYI_DEBUG("SPLASH: unloading Tcl/Tk shared libaries...\n");
    pyi_dylib_tcltk_cleanup(&splash->dylib_tcltk);

    PYI_DEBUG("SPLASH: cleanup complete!\n");
    return 0;
}

/*
 * Allocate memory for splash status
 */
struct SPLASH_CONTEXT *
pyi_splash_context_new()
{
    struct SPLASH_CONTEXT *splash;

    splash = (struct SPLASH_CONTEXT *)calloc(1, sizeof(struct SPLASH_CONTEXT));

    if (splash == NULL) {
        PYI_PERROR("calloc", "Could not allocate memory for SPLASH_CONTEXT.\n");
    }

    return splash;
}

/*
 * Free memory allocated for the splash context structure (the memory
 * allocated for its heap-allocated fields, as well as the structure
 * itself). The splash context structure is passed via pointer to
 * location that stores the structure - this location is also cleared
 * to NULL.
 */
void
pyi_splash_context_free(struct SPLASH_CONTEXT **splash_ref)
{
    struct SPLASH_CONTEXT *splash = *splash_ref;

    *splash_ref = NULL;

    if (splash == NULL) {
        return;
    }

    free(splash->script);
    free(splash->image);
    free(splash->requirements);

    free(splash);
}

/* ----------------------------------------------------------------------------------------- */

/* We can pass data to Tcl interpreter thread or execute functions in it
 * by implementing custom Tcl events. */
struct Splash_Event
{
    Tcl_Event ev; /* must be first */
    struct SPLASH_CONTEXT *splash;
    /* We may wait for the interpreter thread to complete to get
     * a result. For this we use the done condition. The behavior
     * of result and the condition are only defined, if async is false. */
    bool async;
    Tcl_Condition *done;
    int *result;
    /* We let the caller decide which function to execute in the interpreter
     * thread, so we pass an function to the interpreter to execute.
     * The function receives the current SPLASH_CONTEXT and user_data */
    pyi_splash_event_proc *proc;
    const void *user_data;
};

/*
 * We encapsulate the way we post the events to the interpreter
 * thread.
 *
 * In order to safely receive the result, we created a mutex called
 * call_mutex, which controls access to the result field of the Splash_Event
 * (technically, it controls the access to whole Splash_Event, but we only
 * care about the result field). If async is false, we block until the
 * interpreter thread serviced the event.
 */
static void
_splash_event_send(
    struct SPLASH_CONTEXT *splash,
    Tcl_Event *ev,
    Tcl_Condition *cond,
    Tcl_Mutex *mutex,
    bool async
)
{
    const struct DYLIB_TCLTK *dylib_tcltk = splash->dylib_tcltk;

    dylib_tcltk->Tcl_MutexLock(mutex);
    dylib_tcltk->Tcl_ThreadQueueEvent(splash->thread_id, ev, TCL_QUEUE_TAIL);
    dylib_tcltk->Tcl_ThreadAlert(splash->thread_id);

    if (!async) {
        dylib_tcltk->Tcl_ConditionWait(cond, mutex, NULL); /* Wait for the result */
    }

    dylib_tcltk->Tcl_MutexUnlock(mutex);
}

/*
 * This is a wrapper function for the custom proc passed via
 * Splash_Event. It encapsulates the logic to safely return
 * the result of the custom procedure passed to pyi_splash_send.
 * If pyi_splash_send was called with async = true, the result
 * of the custom procedure is discarded; if false was supplied,
 * the variable pointer by result will be updated.
 *
 * Note: this function is executed inside the Tcl interpreter thread.
 */
static int
_splash_event_proc(Tcl_Event *ev, int flags)
{
    int rc = 0;
    struct Splash_Event *splash_event;

    splash_event = (struct Splash_Event *)ev;

    /* Call the custom procedure passed to pyi_splash_send */
    if (splash_event->proc != NULL) {
        rc = (splash_event->proc)(splash_event->splash, splash_event->user_data);
    }

    if (!splash_event->async) {
        struct SPLASH_CONTEXT *splash = splash_event->splash;
        const struct DYLIB_TCLTK *dylib_tcltk = splash->dylib_tcltk;

        /* In synchronous mode, the caller thread is waiting on the
         * wait condition. Notify it that the function call has finished. */
        dylib_tcltk->Tcl_MutexLock(&splash_event->splash->call_mutex);

        *splash_event->result = rc;

        dylib_tcltk->Tcl_ConditionNotify(splash_event->done);
        dylib_tcltk->Tcl_MutexUnlock(&splash_event->splash->call_mutex);
    }

    /* Not an error code; value 1 indicates that event has been processed. */
    return 1;
}

/*
 * To update the splash screen text with the given text, we schedule a
 * Splash_Event into the Tcl interpreter's event queue.
 *
 * This function will update the variable "status_text", which updates the label
 * on the splash screen. We schedule this function in async mode, meaning
 * the main (bootloader) thread does not wait for this function to finish
 * its execution.
 *
 * Note: this function is executed inside the Tcl interpreter thread.
 */
static int
_pyi_splash_text_update(struct SPLASH_CONTEXT *splash, const void *user_data)
{
    const char *text = (const char *)user_data;
    splash->dylib_tcltk->Tcl_SetVar2(splash->interp, "status_text", NULL, text, TCL_GLOBAL_ONLY);
    return 0;
}

/*
 * To update the text on the splash screen, we provide this function,
 * which enqueues an event for the Tcl interpreter thread to service.
 *
 * This function is called from bootloader's main thread, namely from
 * the pyi_launch_extract_files_from_archive while it extracts files
 * from the executable-embedded archive.
 */
int
pyi_splash_update_text(struct SPLASH_CONTEXT *splash, const char *text)
{
    /* We enqueue the _pyi_splash_text_update function into the Tcl
     * interpreter event queue in async mode, ignoring the return value. */
    return pyi_splash_send(splash, true, text, _pyi_splash_text_update);
}

/*
 * To enqueue a function (proc) to be serviced by the Tcl interpreter
 * (therefore interacting with the interpreter), we provide this function
 * to execute the procedure in the Tcl thread.
 *
 * This function supports two execution modes:
 *  - async: activated by setting async to true. In this case the function
 *           is enqueued for processing, but we do not wait for it to be
 *           processed, therefore not blocking the caller (returning after
 *           the function has been scheduled).
 *  - sync:  in this mode the function blocks the calling thread until
 *           the function has been serviced by the Tcl interpreter.
 *           The return value of the enqueued function will be the return
 *           value of this function.
 *
 * All function executed inside the Tcl interpreter thread are holding
 * the status mutex, meaning they can safely modify the SPLASH_CONTEXT.
 */
int
pyi_splash_send(struct SPLASH_CONTEXT *splash, bool async, const void *user_data, pyi_splash_event_proc proc)
{
    int rc = 0;
    struct Splash_Event *ev;
    Tcl_Condition cond = NULL;

    /* Tcl will free this event once it was serviced. */
    ev = (struct Splash_Event *)splash->dylib_tcltk->Tcl_Alloc(sizeof(struct Splash_Event));

    ev->ev.proc = (Tcl_EventProc *)_splash_event_proc;
    ev->splash = splash;

    /* Needed for synchronous return values. */
    ev->async = async;
    ev->done = &cond;
    ev->result = &rc;

    /* The custom procedure to be called. */
    ev->proc = proc;
    ev->user_data = user_data;

    _splash_event_send(splash, (Tcl_Event *)ev, &cond, &splash->call_mutex, async);

    if (!async) {
        splash->dylib_tcltk->Tcl_ConditionFinalize(&cond);
    }
    return rc;
}

/* ----------------------------------------------------------------------------------------- */

/*
 * This is the command handler for the Tcl command `tclInit`
 * By default, `Tcl_Init` defines a internal `tclInit` procedure, which
 * is called in order to find the Tcl standard library. If a `tclInit`
 * command is created/registered by the wrapping C code, it will be called
 * instead.
 *
 * We override the internal function, because we want to run Tcl in a very
 * minimal environment and do not want to initialize the standard library.
 */
static int
_tclInit_Command(ClientData clientData, Tcl_Interp *interp, int objc, Tcl_Obj *const objv[])
{
    /**
     * This function would normally do a search in some common and
     * specific paths to find an `init.tcl` file. Once found, every script
     * next to it would be executed (`auto.tcl`, `clock.tcl`, etc.) to
     * define the standard library.
     * This initialization script would normally set `$auto_path` to be
     * the folder where `init.tcl` was found, usually the `tclX.Y` directory
     * inside python's Tcl distribution directory.
     */
    return TCL_OK;
}

static int
_tcl_findLibrary_Command(ClientData clientData, Tcl_Interp *interp, int objc, Tcl_Obj *const objv[])
{
    /**
     * This function is normally defined inside `auto.tcl`, and searches
     * for modules that Tcl provides via its standard library. It
     * performs a canonical search through different places, for example
     * relative to `$auto_path` and `$tcl_library`.
     *
     * We replace this function with custom implementation in order to run
     * a minimal Tcl environment. This implementation resolves only `tk.tcl`,
     * which is required for Tk initialization in `Tk_Init`:
     *
     * https://github.com/tcltk/tk/blob/core_8_6_7/generic/tkWindow.c#L3326
     *
     * Original function description in auto.tcl:
     *
     *  tcl_findLibrary --
     * 	This is a utility for extensions that searches for a library directory
     * 	using a canonical searching algorithm. A side effect is to source the
     * 	initialization script and set a global library variable.
     *  Arguments:
     *  	basename	Prefix of the directory name, (e.g., "tk")
     * 	    version		Version number of the package, (e.g., "8.0")
     * 	    patch		Patchlevel of the package, (e.g., "8.0.3")
     * 	    initScript	Initialization script to source (e.g., tk.tcl)
     * 	    enVarName	environment variable to honor (e.g., TK_LIBRARY)
     * 	    varName		Global variable to set when done (e.g., tk_library)
     */
    int rc;
    struct SPLASH_CONTEXT *splash = (struct SPLASH_CONTEXT *)clientData;
    const struct DYLIB_TCLTK *dylib_tcltk = splash->dylib_tcltk;
    char initScriptPath[PYI_PATH_MAX];

    /* In our minimal environment, this function is only called once,
     * from Tk_Init. So we only implement the behavior for Tk. Other
     * libraries are therefore not supported. We do not check the version
     * of `tk`, since the library packed by PyInstaller at build time is
     * guaranteed to be compatible. */
    if (strncmp(dylib_tcltk->Tcl_GetString(objv[4]), "tk.tcl", 64) == 0) {
        pyi_path_join(initScriptPath, splash->tk_lib, dylib_tcltk->Tcl_GetString(objv[4]));
        dylib_tcltk->Tcl_SetVar2(interp, "tk_library", NULL, splash->tk_lib, TCL_GLOBAL_ONLY);
        rc = dylib_tcltk->Tcl_EvalFile(interp, initScriptPath);
        return rc;
    }

    /* We do not expect this function to be called for any other library,
     * but just in case, return that the library was not found. */
    return TCL_ERROR;
}

/*
 * The `source` command takes the contents of a specified file or resource
 * and passes it to the Tcl interpreter as a text script.
 *
 * We override this command, because we run Tcl in a minimal environment, in
 * which some files may not be included. At build time, PyInstaller includes
 * only files that are necessary to run the splash screen. If the default
 * `source` command encountered a non-existent file, it would throw an
 * error, which we do not want. In our custom implementation, we therefore
 * silently ignore missing files.
 */
static int
_tcl_source_Command(ClientData clientData, Tcl_Interp *interp, int objc, Tcl_Obj *const objv[])
{
    /* In `_splash_init`, we renamed the original `source` command to `_source`
     * in order  to keep its functionality available. As we know that we are
     * running an error-free script,  we do not do the checks for a valid
     * command, or at least we do it with the original `source` command. */
    struct SPLASH_CONTEXT *splash = (struct SPLASH_CONTEXT *)clientData;
    const struct DYLIB_TCLTK *dylib_tcltk = splash->dylib_tcltk;
    Tcl_Obj **_source_objv;
    int rc;
    int i;

    /* Check if the file to be sourced exists. The filename
     * is always the last (objc-1) parameter passed to the command */
    if (pyi_path_exists(dylib_tcltk->Tcl_GetString(objv[objc - 1]))) {
        /* Create a new objv array for the original source command
         * named _source. */
        _source_objv = (Tcl_Obj **)dylib_tcltk->Tcl_Alloc(sizeof(Tcl_Obj *) * objc);
        _source_objv[0] = dylib_tcltk->Tcl_NewStringObj("_source", -1);

        for (i = 1; i < objc; i++) {
            _source_objv[i] = objv[i];
        }

        /* Execute `_source` with the given arguments */
        rc = dylib_tcltk->Tcl_EvalObjv(interp, objc, _source_objv, 0);
        dylib_tcltk->Tcl_Free((char *) _source_objv);

        return rc;
    }

    /* If the file does not exist, we return OK */
    return TCL_OK;

}

/*
 * The default Tcl `exit` command terminates the whole application;
 * we override it to just exit the main loop, so that the main thread
 * with python interpreter can continue running.
 */
static int
_tcl_exit_Command(ClientData clientData, Tcl_Interp *interp, int objc, Tcl_Obj *const objv[])
{
    struct SPLASH_CONTEXT *splash = (struct SPLASH_CONTEXT *)clientData;
    splash->exit_main_loop = true;
    return TCL_OK;
}

/*
 * This function is executed inside a new thread, in which the Tcl
 * interpreter will run.
 *
 * We create and initialize the Tcl interpreter in this thread since
 * threaded Tcl locks a interpreter to a specific thread at creation.
 * In order to be thread-safe during initialization, we use a Tcl_Mutex
 * called `context_mutex` to lock access to the SPLASH_CONTEXT. This mutex
 * is initially acquired at the point where this thread is created (i.e.,
 * in the main thread, in `pyi_splash_start`). After the main thread
 * finished creating this thread, the `context_mutex` is released, and
 * this thread gets to hold it. It will only be unlocked after the splash
 * screen is closed. This means that all function called through
 * `pyi_splash_send` are called with mutex held, and therefore they are
 * safe to modify SPLASH_CONTEXT.
 *
 * Note: This function will run/setup the Tcl interpreter thread.
 */
static Tcl_ThreadCreateType
_splash_init(ClientData client_data)
{
    int err = 0;
    struct SPLASH_CONTEXT *splash = (struct SPLASH_CONTEXT *)client_data;
    const struct DYLIB_TCLTK *dylib_tcltk = splash->dylib_tcltk;
    Tcl_Obj *image_data_obj;

    dylib_tcltk->Tcl_MutexLock(&splash->context_mutex);

    splash->exit_main_loop = false;

    splash->interp = dylib_tcltk->Tcl_CreateInterp();

    if (splash->thread_id == NULL) {
        /* This should never happen, but as a backup we set the field in here. */
        splash->thread_id = dylib_tcltk->Tcl_GetCurrentThread();
    }

    /* In order to run a minimal Tcl interpreter, we override the `tclInit`
     * command, which is called by Tcl_Init().
     * This is a supported way of modifying Tcl's startup behavior. */
    err |= dylib_tcltk->Tcl_CreateObjCommand(
        splash->interp,
        "tclInit",
        _tclInit_Command,
        splash,
        NULL
    ) == NULL;

    /* Tk_Init calls the Tcl standard library function 'tcl_findLibrary' */
    err |= dylib_tcltk->Tcl_CreateObjCommand(
        splash->interp,
        "tcl_findLibrary",
        _tcl_findLibrary_Command,
        splash,
        NULL
    ) == NULL;

    /* We override the exit command to terminate only this thread and not
     * the whole application. */
    err |= dylib_tcltk->Tcl_CreateObjCommand(
        splash->interp,
        "exit",
        _tcl_exit_Command,
        splash,
        NULL
    ) == NULL;

    /* Replace `source` command for use in minimal environment. */
    dylib_tcltk->Tcl_EvalEx(splash->interp, "rename ::source ::_source", -1, 0);
    err |= dylib_tcltk->Tcl_CreateObjCommand(
        splash->interp,
        "source",
        _tcl_source_Command,
        splash,
        NULL
    ) == NULL;

    /* We OR return values of the Tcl_CreateObjCommand function because
     * if one of them fails, the splash screen should be aborted (and
     * generally, if one fails, all of them should fail). */
    if (err) {
        PYI_DEBUG("TCL: failed to create setup commands. Error: %s\n", dylib_tcltk->Tcl_GetString(dylib_tcltk->Tcl_GetObjResult(splash->interp)));
        goto cleanup;
    }

    /* Initialize Tcl/Tk */
    err |= dylib_tcltk->Tcl_Init(splash->interp);

    if (err) {
        PYI_DEBUG("SPLASH: error while initializing Tcl: %s\n", dylib_tcltk->Tcl_GetString(dylib_tcltk->Tcl_GetObjResult(splash->interp)));
    }

    err |= dylib_tcltk->Tk_Init(splash->interp);

    if (err) {
        PYI_DEBUG("SPLASH: error while initializing Tk: %s\n", dylib_tcltk->Tcl_GetString(dylib_tcltk->Tcl_GetObjResult(splash->interp)));
    }

    if (err) {
        goto cleanup;
    }

    /* Display version of Tcl and Tk for debugging purposes. */
    PYI_DEBUG(
        "SPLASH: running Tcl version %s and Tk version %s.\n",
        dylib_tcltk->Tcl_GetVar2(splash->interp, "tcl_patchLevel", NULL, TCL_GLOBAL_ONLY),
        dylib_tcltk->Tcl_GetVar2(splash->interp, "tk_patchLevel", NULL, TCL_GLOBAL_ONLY)
    );

    /* Extract the image from the splash resources, and pass it to Tcl/Tk
     * via the `_image_data` variable. */
    image_data_obj = dylib_tcltk->Tcl_NewByteArrayObj(splash->image, splash->image_len);
    dylib_tcltk->Tcl_SetVar2Ex(splash->interp, "_image_data", NULL, image_data_obj, TCL_GLOBAL_ONLY);

    /* Tcl/Tk creates a copy of the image, so we can free our buffer */
    free(splash->image);
    splash->image = NULL;

    err = dylib_tcltk->Tcl_EvalEx(splash->interp, splash->script, splash->script_len, TCL_GLOBAL_ONLY);

    if (err) {
        PYI_DEBUG("SPLASH: Tcl error: %s\n", dylib_tcltk->Tcl_GetString(dylib_tcltk->Tcl_GetObjResult(splash->interp)));
    }

    /* We need to notify the bootloader main thread that the splash screen
     * has been started and fully setup */
    dylib_tcltk->Tcl_MutexLock(&splash->start_mutex);
    dylib_tcltk->Tcl_ConditionNotify(&splash->start_cond);
    dylib_tcltk->Tcl_MutexUnlock(&splash->start_mutex);

    /* Main loop.
     * we exit this loop from within tcl. */
    while (dylib_tcltk->Tk_GetNumMainWindows() > 0 && !splash->exit_main_loop) {
        /* Tcl_DoOneEvent blocks this loop until an event is posted into this threads
         * event queue, only after that the condition exit_main_loop is checked again.
         * To unblock this loop while the splash screen is not visible (e.g. receives
         * no events) we post a fake event at finalization (in pyi_splash_finalize) */
        dylib_tcltk->Tcl_DoOneEvent(0);
    }

cleanup:
    /* Synchronize with shutdown/cleanup part in pyi_splash_finalize()
     * to prevent racing against it. */
    dylib_tcltk->Tcl_MutexLock(&splash->exit_mutex);

    PYI_DEBUG("SPLASH: starting clean-up in splash screen thread...\n");

    /* Delete the Tcl interpreter. */
    dylib_tcltk->Tcl_DeleteInterp(splash->interp);
    splash->interp = NULL;

    dylib_tcltk->Tcl_MutexUnlock(&splash->context_mutex);

    /* In case the startup fails the main thread should continue; in
     * normal startup this segment will notify no waiting condition. */
    dylib_tcltk->Tcl_MutexLock(&splash->start_mutex);
    dylib_tcltk->Tcl_ConditionNotify(&splash->start_cond);
    dylib_tcltk->Tcl_MutexUnlock(&splash->start_mutex);

    /* Must be done before exit_wait condition is notified, because
     * we need to ensure that the main thread (which is waiting on it)
     * does not unload the Tcl library before we're done with this
     * Tcl_FinalizeThread() call. */
    dylib_tcltk->Tcl_FinalizeThread();

    /* We notify all conditions waiting for this thread to exit, if
     * there are any. */
    dylib_tcltk->Tcl_ConditionNotify(&splash->exit_wait);
    PYI_DEBUG("SPLASH: clean-up in splash screen thread complete!\n");
    dylib_tcltk->Tcl_MutexUnlock(&splash->exit_mutex);

    TCL_THREAD_CREATE_RETURN;
}
