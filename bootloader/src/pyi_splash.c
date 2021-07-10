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

#ifdef _WIN32
    #include <windows.h>
#endif
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* PyInstaller headers */
#include "pyi_global.h"
#include "pyi_archive.h"
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
 * implemented. To show a splash screen the library tk is used. Tk is accessed by
 * and distributed with tcl inside the python standard library (as of python 3.8
 * with tcl/tk 8.6). Python uses Tcl/Tk in the module tkinter. Tkinter is a wrapper
 * between python and tcl, so using tkinter will use Tcl/Tk. Because tkinter is
 * distributed with any common python installation and it is cross-platform,
 * it is also used for this splash screen.
 *
 * PyInstaller will bundle (if splash screen is enabled) all necessary resources of
 * tcl/tk and append them onto the executable. This results in a slightly bigger
 * application distribution if a splash screen is used, but it is assumed to be negligible.
 *
 * Tcl is a simple high-level programming language like python. It is often embedded into
 * C application for prototyping. Together with Tk (called Tcl/Tk) it is a very powerful
 * tool to build graphical user interfaces and is often used to give C applications
 * a GUI, since it is easy to embed.
 *
 * For this implementation of a tcl/tk wrapper this module loads, if splash screen
 * resouces are appended to the application, the shared libraries of tcl/tk and
 * initializes a minimal tcl/tk environment to run the splash screen from.
 *
 * Only threaded tcl is in this implementation supported, meaning tcl had to be compiled
 * with the --enable-threads flag enabled, which is it by default on Windows and MacOS.
 * Many Linux distributions also come with a threaded tcl installation, although it is not
 * guaranteed. PyInstaller will check at build time if tcl is threaded.
 */

/* Mutexes used for thread safe access to variables */
static Tcl_Mutex status_mutex;
static Tcl_Mutex call_mutex;

/* This mutex/condition is to hold the bootloader until the
 * splash screen has been started */
static Tcl_Mutex start_mutex;
static Tcl_Condition start_cond;

/* These are used to close the splash screen from the main
 * thread. */
static Tcl_Condition exit_wait;
static Tcl_Mutex exit_mutex;
static bool exitMainLoop;

/* Forward declarations */
static Tcl_ThreadCreateProc _splash_init;
typedef struct Splash_Event Splash_Event;

/*
 * Initialize the SPLASH_STATUS by defining the necessary paths
 * and resouces. Those paths and resources are copied from the
 * SPLASH_DATA_HEADER struct.
 *
 * The field data_header may be NULL, in this case the setup routine
 * will call pyi_splash_find() to receive a data header. If none was
 * found NULL is returned and the function stops, not initializing
 * the splash screen.
 * If data_header is supplied the called is responsible for freeing
 * it, if data_header is NULL this function takes care of free the
 * SPLASH_DATA_HEADER.
 */
int
pyi_splash_setup(SPLASH_STATUS *splash_status,
                 ARCHIVE_STATUS *archive_status,
                 SPLASH_DATA_HEADER *data_header)
{
    int _delete_header = 0;

    if (data_header == NULL) {
        if ((data_header = pyi_splash_find(archive_status)) == NULL) {
            /* No splash resources in this application. Close it */
            return -1;
        }
        _delete_header = 1;
    }
    /*
     * We assume first that we run in onedir mode, therefore the tcl and tk
     * libraries are relative to the executable. Only if pyi_splash_extract
     * is called we know that we are in a onefile application.
     * pyi_splash_extract changes these fields again to point to the
     * extracted libraries.
     */
    strncpy(splash_status->tcl_libpath, data_header->tcl_libname, 16);
    strncpy(splash_status->tk_libpath, data_header->tk_libname, 16);
    strncpy(splash_status->rundir, data_header->rundir, 16);

    /* Tcl requires a full path to the tk library. Since we expect at
     * this moment that we are in a onedir application the tk library is in
     * homepath. If we run in onefile, pyi_splash_extract will change this value */
    pyi_path_join(splash_status->tk_lib, archive_status->homepath, data_header->tk_lib);

    /* Copy the script into a buffer owned by SPLASH_STATUS */
    splash_status->script_len = pyi_be32toh(data_header->script_len);
    splash_status->script = (char *) calloc(1, splash_status->script_len + 1);

    /* Copy the image into a buffer owned by SPLASH_STATUS */
    splash_status->image_len = pyi_be32toh(data_header->image_len);
    splash_status->image = (char *) malloc(splash_status->image_len);

    /* Copy the requirements array into a buffer owned by SPLASH_STATUS */
    splash_status->requirements_len = pyi_be32toh(data_header->requirements_len);
    splash_status->requirements = (char *) malloc(splash_status->requirements_len);

    if (splash_status->script == NULL || splash_status->image == NULL ||
        splash_status->requirements == NULL) {
        FATALERROR("Cannot allocate memory for necessary files.\n");
        return -1;
    }

    /* Copy the data into their respective fields */
    memcpy(splash_status->script,
           ((char *) data_header) + pyi_be32toh(data_header->script_offset),
           splash_status->script_len);
    memcpy(splash_status->image,
           ((char *) data_header) + pyi_be32toh(data_header->image_offset),
           splash_status->image_len);
    memcpy(splash_status->requirements,
           ((char *) data_header) + pyi_be32toh(data_header->requirements_offset),
           splash_status->requirements_len);

    /* If data_header was NULL, we allocated it, so we should free it too */
    if (_delete_header) {
        free(data_header);
    }

    return 0;
}

/*
 * Start the splash screen.
 * This function is only safe to call, if the tcl/tk libraries
 * have been attached, since in the attached functions are used.
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
pyi_splash_start(SPLASH_STATUS *status, const char *executable)
{
    PI_Tcl_MutexLock(&status_mutex);

    if (status->dll_tcl == NULL || status->dll_tk == NULL) {
        /* Make sure the libraries are attached */
        return -1;
    }

    /* This functions needs to be called before everything else is done
     * with Tcl, otherwise the behavior of tcl is undefined. */
    PI_Tcl_FindExecutable(executable);

    /* We try to create a new thread (in which the tcl interpreter will run) with
     * a methods provided by tcl. This function will return TCL_ERROR if it is
     * either not implemented (tcl is not threaded) or an error occurs.
     * Since we only support threaded tcl we return on error */
    if (PI_Tcl_CreateThread(&status->thread_id,   /* Where to store the thread id */
                            _splash_init,         /* Proc to run in new thread */
                            status,               /* Parameter to proc */
                            0,                    /* Use default stack size */
                            0) != TCL_OK) {       /* no flags */
        FATALERROR("SPLASH: Tcl is not threaded. Only threaded tcl is supported.\n");
        PI_Tcl_MutexUnlock(&status_mutex);
        pyi_splash_finalize(status);
        return -1;
    }
    PI_Tcl_MutexLock(&start_mutex);
    PI_Tcl_MutexUnlock(&status_mutex);

    VS("SPLASH: Created thread for tcl interpreter.\n");

    /* To avoid a race condition between the tcl and python interpreter
     * we need to wait until the splash screen has been started. We lock
     * here until the tcl thread notified us, that it has finished starting up.
     * See discarded idea in pyi_splash python module */
    PI_Tcl_ConditionWait(&start_cond, &start_mutex, NULL);
    PI_Tcl_MutexUnlock(&start_mutex);
    PI_Tcl_ConditionFinalize(&start_cond);
    VS("SPLASH: Splash screen started.\n");

    return 0;
}

/*
 * Searches the CArchive for splash screen resources and returns a pointer
 * to its header. The fields inside the SPLASH_DATA_HEADER define the
 * necessary parts to load and to create the splash screen. If no splash
 * screen resources are found, NULL is returned.
 *
 * The splash screen resources are identified in the CArchive by the type
 * code 'ARCHIVE_ITEM_SPLASH'.
 *
 * The SPLASH_DATA_HEADER structure is, if loaded from archive,
 * in network endian, so it must be converted when used.
 *
 * This function is called by pyi_splash_setup in order to setup
 * SPLASH_STATUS (assuming pyi_splash_setup data_header field is NULL).
 */
SPLASH_DATA_HEADER *
pyi_splash_find(ARCHIVE_STATUS *status)
{
    SPLASH_DATA_HEADER *header = NULL;
    TOC *ptoc = status->tocbuff;

    while (ptoc < status->tocend) {
        if (ptoc->typcd == ARCHIVE_ITEM_SPLASH) {
            header = (SPLASH_DATA_HEADER *) pyi_arch_extract(status, ptoc);
            VS("SPLASH: Found splash screen resources.\n");
            break;
        }
        ptoc = pyi_arch_increment_toc_ptr(status, ptoc);
    }

    return header;
}

/*
 * Extract the necessary parts of the splash screen resources from
 * the archive, if they are bundled. Those resources are required to
 * be on the filesystem. If no dependencies are in the archive, this function
 * does nothing.
 *
 * Since these extracted files would collide with the files the loop inside
 * pyi_launch_extract_binaries extracts, we put the splash screen files into
 * a subdirectory inside archive_status->temppath. The name of the subdirectory
 * is provided by the SPLASH_DATA_HEADER "rundir" field, which is ensured to not
 * collide with any custom directory the users program includes.
 *
 * Unpacking into a subdirectory creates a small inefficiency, because
 * the loop in pyi_launch_extract_binaries unpacks these files again later.
 */
int
pyi_splash_extract(ARCHIVE_STATUS *archive_status, SPLASH_STATUS *splash_status)
{
    /*
     * Alternative implementations considered:
     *    - Implementing a check in pyi_launch_extract_binaries if an already extracted
     *      and therefore in temppath existing file belongs to the splash screen.
     *      -> Discarded this idea, because SPLASH_STATUS would need to be passed
     *         down to pyi_open_target and for every file already extracted a loop
     *         through the archive would need to check if it belongs to the splash screen
     *    - Implementing a "prioritized" TOC, which starts at a specific level to extract
     *      files. If splash resources are appended these would be extracted, because they
     *      would get the level e.g. 0 assigned. After this extracting those resources only
     *      files with levels >0 would be extracted.
     *      -> Discarded this idea, because it would need a huge rewrite of the current TOC
     *         system in PyInstaller and the bootloader
     */
    size_t pos;
    TOC *tmp_toc, *ptoc;
    int rc = 0;
    bool extracted = false;
    char *filename;
    char tmp[PATH_MAX];
    char run_dir[PATH_MAX];

    /* The last item in TOC is a path, so limit it is at PATH_MAX */
    tmp_toc = (TOC*) calloc(1, sizeof(TOC) + PATH_MAX);

    /* Iterate over the requirements array */
    for (pos = 0; pos < splash_status->requirements_len; pos += strlen(filename) + 1) {
        filename = splash_status->requirements + pos;

        if ((ptoc = pyi_arch_find_by_name(archive_status, filename)) != NULL) {
            /* If there was a requirement in the archive, we assume that we are in
             * a onefile archive, so we try to extract all dependencies and update
             * the paths */
            extracted = true;
            /*
             * Copy the TOC into a new buffer, because we need to modify
             * the TOCs name in order to change its extractionpath.
             * The name is changed to move the file into a directory named
             * after the value of rundir. This is necessary, since the extraction
             * of the rest of the files would collide with these files.
             */
            memcpy(tmp_toc, ptoc, ptoc->structlen);
            pyi_path_join(tmp_toc->name, splash_status->rundir, ptoc->name);
            tmp_toc->structlen = ptoc->structlen - (int) strlen(ptoc->name) + (int) strlen(tmp_toc->name);

            /* Extract file into the rundir */
            if (pyi_arch_extract2fs(archive_status, tmp_toc)) {
                FATALERROR("SPLASH: Cannot extract requirement %s.\n", ptoc->name);
                rc = -2;
                goto cleanup;
            }
        }
        else if (extracted) {
            /* We extracted previously some files but we didnt find this one, so
             * the dependency is not available */
            FATALERROR("SPLASH: Cannot find requirement %s in archive.\n", filename);
            rc = -1;
            goto cleanup;
        }
    }

    if (extracted) {
        /* Alter the paths inside SPLASH_STATUS to load the the libraries from the
         * correct place */
        pyi_path_join(run_dir, archive_status->temppath, splash_status->rundir);

        strncpy(tmp, splash_status->tcl_libpath, PATH_MAX);
        pyi_path_join(splash_status->tcl_libpath, run_dir, tmp);

        strncpy(tmp, splash_status->tk_libpath, PATH_MAX);
        pyi_path_join(splash_status->tk_libpath, run_dir, tmp);

        pyi_path_basename(tmp, splash_status->tk_lib);
        pyi_path_join(splash_status->tk_lib, run_dir, tmp);
    }

cleanup:
    free(tmp_toc);
    return rc;
}

/*
 * Attach tcl/tk functions to this process
 * On success 0 will be returned. A nonzero return
 * code indicates, that an error occurred.
 */
int
pyi_splash_attach(SPLASH_STATUS *status)
{
    VS("SPLASH: Load Tcl library from: %s\n", status->tcl_libpath);
    VS("SPLASH: Load Tk library from: %s\n", status->tk_libpath);

    status->dll_tcl = pyi_utils_dlopen(status->tcl_libpath);
    status->dll_tk = pyi_utils_dlopen(status->tk_libpath);

    if (status->dll_tcl == 0 || status->dll_tk == 0) {
        FATALERROR("LOADER: Failed to load tcl/tk libraries\n");
        return -1;
    }

    /* Attach library to this process */
    return pyi_splashlib_attach(status->dll_tcl, status->dll_tk);
}

/*
 * Finalizes the splash screen.
 * This function is normally called at exiting the splash screen.
 */
int
pyi_splash_finalize(SPLASH_STATUS *status)
{
    if (status != NULL) {
        if (status->thread_id == PI_Tcl_GetCurrentThread()) {
            /* We are in the interpreter thread */
            if (status->interp != NULL) {
                /* We can only call this function safely, if we are
                 * in the tcl interpreter thread */
                PI_Tcl_DeleteInterp(status->interp);
                /* prevent dangling pointers */
                status->interp = NULL;
            }
        }
        else {
            /* We run in the bootloader thread */
            if (status->interp != NULL) {
                /* We notify the tcl thread, if it still exists
                 * to exit and wait for it */
                PI_Tcl_MutexLock(&exit_mutex);
                exitMainLoop = true;
                /* We need to post a fake event into the event queue in order
                 * to unblock Tcl_DoOneEvent, so the main loop can exit */
                pyi_splash_send(status, true, NULL, NULL);
                PI_Tcl_ConditionWait(&exit_wait, &exit_mutex, NULL);
                PI_Tcl_MutexUnlock(&exit_mutex);
                PI_Tcl_ConditionFinalize(&exit_wait);
            }
            /* This function should only be called after python has been
             * destroyed with Py_Finalize. Tcl/Tk/tkinter do **not** support
             * multiple instances of themselves due to restrictions of Tcl
             * (for reference see _tkinter PyMethodDef m_size field or
             * disabled registration of Tcl_Finalize inside _tkinter.c)
             * The python program may have imported tkinter, which keeps
             * its own tcl interpreter. If we finalized Tcl here, the
             * Tcl interpreter of tkinter would also be finalized, resulting
             * in a weird state of tkinter. */
            PI_Tcl_Finalize();

            /* If the dll's aren't already unloaded/still valid
             * unload them, since otherwise the files of the
             * libraries cannot be deleted */
            if (status->dll_tcl != NULL) {
                pyi_utils_dlclose(status->dll_tcl);
                status->dll_tcl = NULL;
                status->is_tcl_loaded = false;
            }

            if (status->dll_tk != NULL) {
                pyi_utils_dlclose(status->dll_tk);
                status->dll_tk = NULL;
                status->is_tk_loaded = false;
            }
        }
    }
    return 0;
}

/*
 * Allocate memory for splash status
 */
SPLASH_STATUS *
pyi_splash_status_new()
{
    SPLASH_STATUS *splash_status;

    splash_status = (SPLASH_STATUS *) calloc(1, sizeof(SPLASH_STATUS));

    if (splash_status == NULL) {
        FATAL_PERROR("calloc", "Cannot allocate memory for SPLASH_STATUS.\n");
    }
    return splash_status;
}

/*
 * Free memory allocated for splash status.
 * Note that this function will also set the passed
 * reference to the SPLASH_STATUS to NULL.
 */
void
pyi_splash_status_free(SPLASH_STATUS **splash_status)
{
    SPLASH_STATUS *_status = (SPLASH_STATUS*) *splash_status;

    if (_status != NULL) {
        if (_status->script != NULL) {
            free(_status->script);
        }

        if (_status->image != NULL) {
            free(_status->image);
        }

        if (_status->requirements != NULL) {
            free(_status->requirements);
        }

        free(_status);
    }
    *splash_status = NULL;
}

/* ----------------------------------------------------------------------------------------- */

/* Through implementing a custom tcl event we can pass data to the
 * interpreter thread or execute functions in it */
struct Splash_Event {
    Tcl_Event      ev;          /* Must be first */
    SPLASH_STATUS *status;
    /* We may wait for the interpreter thread to complete to get
     * a result. For this we use the done condition. The behavior
     * of result and the condition are only defined, if async is false */
    bool           async;
    Tcl_Condition *done;
    int *          result;
    /* We let the caller decide which function to execute in the interpreter
     * thread, so we pass an function to the interpreter to execute.
     * The function receives the current SPLASH_STATUS and user_data */
    pyi_splash_event_proc *proc;
    void *                 user_data;
};

/*
 * We encapsulate the way we post the events to the interpreter
 * thread.
 *
 * In order to safely receiving the result we created a mutex called
 * call_mutex, which controls access to the result field of the Splash_Event
 * (technically controls the whole access to Splash_Event, but we only
 * care for the result field). If async is true we don't bock
 * until the interpreter thread serviced the event.
 */
static void
_splash_event_send(SPLASH_STATUS *status, Tcl_Event *ev, Tcl_Condition *cond,
                   Tcl_Mutex *mutex, bool async)
{
    PI_Tcl_MutexLock(mutex);
    PI_Tcl_ThreadQueueEvent(status->thread_id, ev, TCL_QUEUE_TAIL);
    PI_Tcl_ThreadAlert(status->thread_id);

    if (!async) {
        /* If we want to wait for the result of the thread we wait
         * for the condition to be notified */
        PI_Tcl_ConditionWait(cond, mutex, NULL);
    }
    PI_Tcl_MutexUnlock(mutex);
}

/*
 * This is a wrapper function for the custom proc passed via
 * Splash_Event. It encapsulates the logic to safely return
 * the result of the custom procedure passed to pyi_splash_send.
 * If pyi_splash_send was called with async = true, the result
 * of the custom procedure is discarded, if false was supplied
 * the variable pointer by result will be updated.
 *
 * Note: This function is executed inside the tcl interpreter thread
 */
int
_splash_event_proc(Tcl_Event *ev, int flags)
{
    int rc = 0;
    Splash_Event *splash_event;

    splash_event = (Splash_Event *) ev;

    /* Call the custom procedure passed to pyi_splash_send */
    if (splash_event->proc != NULL) {
        rc = (splash_event->proc)(splash_event->status, splash_event->user_data);
    }

    if (!splash_event->async) {
        /* If the custom function called should block until the event was
         * serviced the main thread (in which the bootloader runs) waits
         * on the Tcl_Condition, which we notify now, that we are finished */
        PI_Tcl_MutexLock(&call_mutex);

        *splash_event->result = rc;

        PI_Tcl_ConditionNotify(splash_event->done);
        PI_Tcl_MutexUnlock(&call_mutex);
    }

    return 1;  /* Not an error code, this indicates, that the event is satisfied */
}

/*
 * To update the text on the splash screen with the current item unpacking
 * we schedule a Splash_Event into the tcl interpreters event queue.
 *
 * This function will update the variable "status_text", which updated the label
 * on the splash screen. We schedule this function in async mode, meaning we
 * the main (bootloader) thread does not wait until this function executed.
 *
 * Note: This function is executed inside the tcl interpreter thread
 */
int
_pyi_splash_progress_update(SPLASH_STATUS *status, void *user_data)
{
    TOC *ptoc;

    ptoc = (TOC *) user_data;

    PI_Tcl_SetVar2(status->interp, "status_text", NULL, ptoc->name, TCL_GLOBAL_ONLY);

    return 0;
}

/*
 * To update the text on the splash screen (optionally) we provide
 * this function, which enqueues an event for the tcl interpreter
 * thread to service. We update the text based on the name gave by ptoc
 *
 * This function is called from within pyi_launch_extract_binaries to
 * update which file is currently in the progress of being
 * unpacked.
 */
int
pyi_splash_update_prg(SPLASH_STATUS *status, TOC *ptoc)
{
    /* We enqueue the _pyi_splash_progress_update function into the tcl
     * interpreter event queue in async mode, ignoring the return value. */
    return pyi_splash_send(status, true, ptoc, _pyi_splash_progress_update);
}

/*
 * To enqueue a function (proc) to be serviced by the tcl interpreter
 * (therefore interacting with the interpreter) we provide this function to
 * execute the procedure in the tcl thread.
 *
 * This function supports two ways:
 *  - async: Activated by setting async to true. In this case the function
 *           is enqueued for processing, but we don't wait for it to be
 *           processed, therefore not blocking the caller (returning after
 *           the function has been scheduled).
 *  - sync:  In this mode the function blocks the calling thread until
 *           the function has been serviced by the tcl interpreter.
 *           The return value of the enqueued function will be the return
 *           value of this function.
 *
 * All function executed inside the tcl interpreter thread are holding
 * the status mutex, meaning they are allowed to modify the SPLASH_STATUS
 * safely.
 */
int
pyi_splash_send(SPLASH_STATUS *status, bool async, void *user_data,
                pyi_splash_event_proc proc)
{
    int rc = 0;
    Splash_Event *ev;
    Tcl_Condition cond = NULL;

    /* Tcl will free this event once it was serviced */
    ev = (Splash_Event *) PI_Tcl_Alloc(sizeof(Splash_Event));

    ev->ev.proc = (Tcl_EventProc *) _splash_event_proc;
    ev->status = status;

    /* Needed for synchronous return values */
    ev->async = async;
    ev->done = &cond;
    ev->result = &rc;

    /* The custom procedure to be called */
    ev->proc = proc;
    ev->user_data = user_data;

    _splash_event_send(status, (Tcl_Event *) ev, &cond, &call_mutex, async);

    if (!async) {
        PI_Tcl_ConditionFinalize(&cond);
    }
    return rc;
}

/* ----------------------------------------------------------------------------------------- */

/*
 * This is the command handler for the tcl command 'tclInit'
 * By default Tcl_Init defines a internal tclInit procedure, which
 * is called in order to find the tcl standard library. If a tclInit
 * command is created/registered by the wrapping C code, it will be called
 * instead.
 *
 * We override the internal function, because we want to run tcl in a very
 * minimal environment and dont want to initialize the standard library.
 */
int
_tclInit_Command(ClientData clientData, Tcl_Interp *interp,
                 int objc, Tcl_Obj *const objv[])
{
    /**
     * This function would normally do a search in some common and
     * specific paths to find a init.tcl file. Once found every script
     * around it would be executed (auto.tcl, clock.tcl, etc.) to define
     * the standard library.
     * This initialization script would normally set $auto_path to be
     * the folder where init.tcl was found. This is normally tclX.Y
     * inside python's tcl distribution folder
     */
    return TCL_OK;
}

int
_tcl_findLibrary_Command(ClientData clientData, Tcl_Interp *interp,
                         int objc, Tcl_Obj *const objv[])
{
    /**
     * To find a module tcl provides this function via it's standard
     * library (this function is normally defined inside auto.tcl).
     * It does a canonical search through different places like relative
     * to $auto_path and $tcl_library.
     * We replace this function with this implementation in order to run
     * a minimal tcl environment.
     *
     * Tk calls upon initialization_ (Tk_Init) the function tcl_findLibrary, which
     * is normally defined in auto.tcl, but since we try to run tcl/tk in a very
     * minimal environment we want to exclude everything unnecessary.
     * Tk asks this function to find tk.tcl. Once found every file around it
     * gets executed to fully setup tk.
     *
     * .. _initialization: https://github.com/tcltk/tk/blob/core_8_6_7/generic/tkWindow.c#L3326
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
    SPLASH_STATUS *status;
    char initScriptPath[PATH_MAX];

    status = (SPLASH_STATUS *) clientData;

    /*
     * In our environment this function is only called once and that is
     * from Tk_Init. So we only implement the behavior for tk. Other libraries
     * are therefore not supported.
     * We don't check the version of tk, since the library packed by PyInstaller
     * at build time are compatible.
     */
    if (strncmp(PI_Tcl_GetString(objv[4]), "tk.tcl", 64) == 0) {
        /* Called to look for tk.tcl */
        pyi_path_join(initScriptPath, status->tk_lib, PI_Tcl_GetString(objv[4]));
        PI_Tcl_SetVar2(interp, "tk_library", NULL, status->tk_lib, TCL_GLOBAL_ONLY);
        rc = PI_Tcl_EvalFile(interp, initScriptPath);
        return rc;
    }

    /* We don't expect this function to be called for any other library,
     * but just in case return that the library was not found. */
    return TCL_ERROR;
}

/*
 * The source command takes the contents of a specified file or resource
 * and passes it to the Tcl interpreter as a text script.
 *
 * We override this command, because we run tcl in a minimal environment, in
 * which some files may not be included. PyInstaller includes at build time
 * all necessary files to run the splash screen and excludes all unnecessary
 * ones. If the default 'source' command would encounter a not existing file it
 * would throw an error, which we don't want. So the extension of this command is
 * that we first check if the file exists and if it does we execute it.
 */
int
_tcl_source_Command(ClientData clientData, Tcl_Interp *interp,
                    int objc, Tcl_Obj *const objv[])
{
    /*
     * In _splash_init we renamed the original source command to _source
     * to keep the functionality of the original source command.
     * Since we know that we are running an error-free script we don't
     * do the checks for a valid command, or at least we do it with the original
     * source command.
     */
    int i, rc;
    Tcl_Obj **_source_objv;

    /* Check if the file to be sourced exists. The filename
     * is always the last (objc-1) parameter passed to the command */
    if (pyi_path_exists(PI_Tcl_GetString(objv[objc - 1]))) {
        /* Create a new objv array for the original source command
         * named _source. */
        _source_objv = (Tcl_Obj **) PI_Tcl_Alloc(sizeof(Tcl_Obj *) * objc);
        _source_objv[0] = PI_Tcl_NewStringObj("_source", -1);

        for (i = 1; i < objc; i++) {
            _source_objv[i] = objv[i];
        }

        /* Execute _source with the given arguments */
        rc = PI_Tcl_EvalObjv(interp, objc, _source_objv, 0);
        PI_Tcl_Free((char *) _source_objv);

        return rc;
    }

    /* If the file does not exist, we return OK */
    return TCL_OK;

}

/*
 * The default tcl exit command terminates the whole application,
 * we override it to just exit the main loop, so the python interpreter
 * can continue to run.
 */
int
_tcl_exit_Command(ClientData clientData, Tcl_Interp *interp,
                  int objc, Tcl_Obj *const objv[])
{
    exitMainLoop = true;
    return TCL_OK;
}

/*
 * This function is executed inside a new thread, in which the tcl
 * interpreter will run.
 *
 * We create and initialize the tcl interpreter in this thread since
 * threaded tcl locks a interpreter to a specific thread at creation.
 * In order to be thread safe while during this we use the a Tcl_Mutex
 * on the SPLASH_STATUS 'status_mutex', which should be used from the
 * point on where this thread got created (in pyi_splash_start). After
 * the main thread finished creating this thread, the status_mutex
 * is released and this thread gets to hold it. It will only be
 * unlocked after the splash screen was closed. This renders all
 * function called through pyi_splash_send to hold the lock and therefore
 * they are safe to manipulate it.
 *
 * Note: This function will run/setup the tcl interpreter thread.
 */
static Tcl_ThreadCreateType
_splash_init(ClientData client_data)
{
    int err = 0;
    SPLASH_STATUS *status;
    Tcl_Obj *image_data_obj;

    PI_Tcl_MutexLock(&status_mutex);

    status = (SPLASH_STATUS *) client_data;
    exitMainLoop = false;

    status->interp = PI_Tcl_CreateInterp();

    if (status->thread_id == NULL) {
        /* This should never happen, but as a backup we set the
         * field in here */
        status->thread_id = PI_Tcl_GetCurrentThread();
    }

    /* In order to run a minimal tcl interpreter we override
     * the tclInit command, which is called by Tcl_Init().
     * This is a supported way of modifying tcl's startup behavior */
    err |= PI_Tcl_CreateObjCommand(status->interp,
                                   "tclInit",
                                   _tclInit_Command,
                                   status,
                                   NULL) == NULL;

    /* Tk_Init calls the tcl standard library function 'tcl_findLibrary' */
    err |= PI_Tcl_CreateObjCommand(status->interp,
                                   "tcl_findLibrary",
                                   _tcl_findLibrary_Command,
                                   status,
                                   NULL) == NULL;

    /* We override the exit command to terminate only this thread and not
     * the whole application */
    err |= PI_Tcl_CreateObjCommand(status->interp,
                                   "exit",
                                   _tcl_exit_Command,
                                   status,
                                   NULL) == NULL;

    /* replace source command for usage in minimal environment */
    PI_Tcl_EvalEx(status->interp, "rename ::source ::_source", -1, 0);
    err |= PI_Tcl_CreateObjCommand(status->interp,
                                   "source",
                                   _tcl_source_Command,
                                   status,
                                   NULL) == NULL;

    /* We OR every return value of the Tcl_CreateObjCommand function because
     * if one of them fails (if one fails every other should fail to) the
     * splash screen should be aborted. */
    if (err) {
        VS("TCL: Cannot create setup commands. Error: %s\n",
           PI_Tcl_GetString(PI_Tcl_GetObjResult(status->interp)));
        goto cleanup;
    }

    /* Initialize Tcl/Tk */
    err |= PI_Tcl_Init(status->interp);

    if (err) {
        VS("SPLASH: Error initializing Tcl. %s\n",
           PI_Tcl_GetString(PI_Tcl_GetObjResult(status->interp)));
    }

    err |= PI_Tk_Init(status->interp);

    if (err) {
        VS("SPLASH: Error initializing Tk. %s\n",
           PI_Tcl_GetString(PI_Tcl_GetObjResult(status->interp)));
    }

    if (err) {
        goto cleanup;      /* If an error occurred exit */

    }
    /* Update the splash status, that tcl and tk
     * are initialized */
    status->is_tcl_loaded = true;
    status->is_tk_loaded = true;

    /* Print version if tcl and tk for debugging */
    VS("SPLASH: Running tcl version %s and tk version %s.\n",
       PI_Tcl_GetVar2(status->interp, "tcl_patchLevel", NULL, TCL_GLOBAL_ONLY),
       PI_Tcl_GetVar2(status->interp, "tk_patchLevel", NULL, TCL_GLOBAL_ONLY));

    /* Extract the image from the splash resouces and
     * pass them to tcl/tk in the variable _image_data */
    image_data_obj = PI_Tcl_NewByteArrayObj(status->image, status->image_len);
    PI_Tcl_SetVar2Ex(status->interp, "_image_data", NULL, image_data_obj,
                     TCL_GLOBAL_ONLY);
    /* Tcl/Tk creates a copy of the image, so we can free our buffer */
    free(status->image);
    status->image = NULL;

    err = PI_Tcl_EvalEx(status->interp, status->script, status->script_len,
                        TCL_GLOBAL_ONLY);

    if (err) {
        VS("TCL Error: %s\n",
           PI_Tcl_GetString(PI_Tcl_GetObjResult(status->interp)));
    }

    /* We need to notify the bootloader main thread that the splash screen
     * has been started and fully setup */
    PI_Tcl_MutexLock(&start_mutex);
    PI_Tcl_ConditionNotify(&start_cond);
    PI_Tcl_MutexUnlock(&start_mutex);

    /* Main loop.
     * we exit this loop from within tcl. */
    while (PI_Tk_GetNumMainWindows() > 0 && !exitMainLoop) {
        /* Tcl_DoOneEvent blocks this loop until an event is posted into this threads
         * event queue, only after that the condition exitMainLoop is checked again.
         * To unblock this loop while the splash screen is not visible (e.g. receives
         * no events) we post a fake event at finalization (in pyi_splash_finalize) */
        PI_Tcl_DoOneEvent(0);
    }

cleanup:
    pyi_splash_finalize(status);
    PI_Tcl_MutexUnlock(&status_mutex);

    /* In case the startup fails the main thread should continue,
     * in normal startup this segment will notify no waiting condition */
    PI_Tcl_MutexLock(&start_mutex);
    PI_Tcl_ConditionNotify(&start_cond);
    PI_Tcl_MutexUnlock(&start_mutex);

    /* Must be done before exit_wait condition is notified, because
     * we need to ensure that the main thread (which is waiting on it)
     * doesn't unload the Tcl library before we're done with this
     * Tcl_FinalizeThread() call.
     */
    PI_Tcl_FinalizeThread();

    /* We notify all conditions waiting for this thread to exit,
     * if there are any */
    PI_Tcl_MutexLock(&exit_mutex);
    PI_Tcl_ConditionNotify(&exit_wait);
    PI_Tcl_MutexUnlock(&exit_mutex);

    TCL_THREAD_CREATE_RETURN;
}
