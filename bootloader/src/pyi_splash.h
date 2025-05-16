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

#ifndef PYI_SPLASH_H
#define PYI_SPLASH_H

#include "zlib.h"
#include "pyi_global.h"
#include "pyi_archive.h"
#include "pyi_dylib_tcltk.h"

/* Archive item header for splash data
 * This struct is a header describing the rest of this archive item */
struct SPLASH_DATA_HEADER
{
    /* Filename of the Tcl shared library, e.g., tcl86t.dll */
    char tcl_libname[32];

    /* Filename of the Tk shared library, e.g. tk86t.dll */
    char tk_libname[32];

    /* Tk module library root, e.g. "tk/" */
    char tk_lib[16];

    /* Splash screen script */
    uint32_t script_len;
    uint32_t script_offset;

    /* Image data */
    uint32_t image_len;
    uint32_t image_offset;

    /*
     * To only extract the necessary files from the archive, the following
     * two fields define an array of strings. Strings are NULL-terminated
     * and stored one after another.
     */
    uint32_t requirements_len;
    uint32_t requirements_offset;

    /*
     * Followed by a chunk of data, including the splash screen
     * script, the image, and the required files array.
     */
};

/* Runtime context for the splash screen */
struct SPLASH_CONTEXT
{
    /* Mutexes used for thread-safe access to context and its variables. */
    Tcl_Mutex context_mutex;
    Tcl_Mutex call_mutex;

    /* This mutex/condition is to hold the bootloader until the splash screen
     * has been started */
    Tcl_Mutex start_mutex;
    Tcl_Condition start_cond;

    /* These are used to close the splash screen from the main thread. */
    Tcl_Condition exit_wait;
    Tcl_Mutex exit_mutex;
    bool exit_main_loop;

    /* The Tcl interpreter in which the splash screen will run. Runs
     * in a secondary thread, as we cannot block the program's primary
     * thread (which in onedir mode needs to run user's python program
     * in python interpreter). */
    Tcl_Interp *interp;

    /* The ID of the thread in which the Tcl interpreter (and thus
     * splash screen) is running. Used to determine if splash context
     * functions are called from the program's main thread or from
     * the Tcl interpreter's (i.e., secondary) thread. */
    Tcl_ThreadId thread_id;

    /* Flag indicating whether thread was created in joinable mode or
     * not. At the time of writing, Tcl on Windows does not support
     * joinable threads. */
    bool thread_joinable;

    /* The paths to Tcl/Tk shared libraries and Tk module library directory.
     * These are anchored to application's top-level directory (static
     * or temporary, depending on onedir vs. onefile mode). */
    char tcl_libpath[PYI_PATH_MAX];
    char tk_libpath[PYI_PATH_MAX];
    char tk_lib[PYI_PATH_MAX];

    /* The Tcl script that creates splash screen and the IPC mechanism
     * to communicate with python code. */
    char *script;
    int script_len;

    /* Image to be show on the splash screen.
     * The image data pointer will eventually be NULL, because it is only
     * kept until the Tcl interpreter is fully set up, at which point it
     * copies the image data into its own data buffer. */
    void *image;
    int image_len;

    /* To start Tcl/Tk, its files need to be present on the filesystem.
     * These fields describe an array of NULL-terminated strings, that
     * contain filenames of files that need to be extracted from
     * PKG/CArchive in onefile mode before splash screen can be started. */
    char *requirements;
    int requirements_len;

    /* Structure that encapsulates loaded Tcl and Tk shared library and
     * pointers to imported functions. */
    struct DYLIB_TCLTK *dylib_tcltk;
};

typedef int (pyi_splash_event_proc)(struct SPLASH_CONTEXT *, const void *);

struct PYI_CONTEXT;


/**
 * Public API functions for pyi_splash
 */
int pyi_splash_setup(struct SPLASH_CONTEXT *splash, const struct PYI_CONTEXT *pyi_ctx);

int pyi_splash_load_shared_libaries(struct SPLASH_CONTEXT *splash);
int pyi_splash_finalize(struct SPLASH_CONTEXT *splash);
int pyi_splash_start(struct SPLASH_CONTEXT *splash, const char *executable);

/* Archive helper functions */
int pyi_splash_extract(struct SPLASH_CONTEXT *splash, const struct PYI_CONTEXT *pyi_ctx);
int pyi_splash_is_splash_requirement(struct SPLASH_CONTEXT *splash, const char *name);

int pyi_splash_send(
    struct SPLASH_CONTEXT *splash,
    bool async,
    const void *user_data,
    pyi_splash_event_proc proc
);
int pyi_splash_update_text(struct SPLASH_CONTEXT *splash, const char *toc_entry_name);

/* Memory allocation functions */
struct SPLASH_CONTEXT *pyi_splash_context_new();
void pyi_splash_context_free(struct SPLASH_CONTEXT **splash_ref);

#endif /*PYI_SPLASH_H */
