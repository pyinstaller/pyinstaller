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
#include "pyi_main.h"
#include "pyi_archive.h"
#include "pyi_splashlib.h"

/* Archive item header for splash data
 * This struct is a header describing the rest of this archive item */
typedef struct _splash_data_header
{
    /* Filename of the Tcl shared library, e.g., tcl86t.dll */
    char tcl_libname[16];

    /* Filename of the Tk shared library, e.g. tk86t.dll */
    char tk_libname[16];

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
} SPLASH_DATA_HEADER;

/* Runtime context for the splash screen */
typedef struct _splash_context
{
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

    /* The paths to Tcl/Tk shared libraries and Tk module library directory.
     * These are anchored to application's top-level directory (static
     * or temporary, depending on onedir vs. onefile mode). */
    char tcl_libpath[PATH_MAX];
    char tk_libpath[PATH_MAX];
    char tk_lib[PATH_MAX];

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

    /* Flag indicating that Tcl/Tk shared libraries were successfully
     * loaded and that required symbols have been loaded and bound. This
     * is primarily used during finalization to properly handle tear-down
     * of partially-initialized splash screen. */
    bool dlls_fully_loaded;

    /* Keep the handles to loaded shared libraries, in order to close them
     * during finalization. */
    dylib_t dll_tcl;
    dylib_t dll_tk;
} SPLASH_CONTEXT;

typedef int (pyi_splash_event_proc)(SPLASH_CONTEXT *, const void *);

/**
 * Public API functions for pyi_splash
 */
int pyi_splash_setup(SPLASH_CONTEXT *splash, const PYI_CONTEXT *pyi_ctx);

int pyi_splash_load_shared_libaries(SPLASH_CONTEXT *splash);
int pyi_splash_finalize(SPLASH_CONTEXT *splash);
int pyi_splash_start(SPLASH_CONTEXT *splash, const char *executable);

/* Archive helper functions */
int pyi_splash_extract(SPLASH_CONTEXT *splash, const PYI_CONTEXT *pyi_ctx);
int pyi_splash_is_splash_requirement(SPLASH_CONTEXT *splash, const char *name);

int pyi_splash_send(
    SPLASH_CONTEXT *splash,
    bool async,
    const void *user_data,
    pyi_splash_event_proc proc
);
int pyi_splash_update_text(SPLASH_CONTEXT *splash, const char *toc_entry_name);

/* Memory allocation functions */
SPLASH_CONTEXT *pyi_splash_context_new();
void pyi_splash_context_free(SPLASH_CONTEXT **splash_ref);

#endif /*PYI_SPLASH_H */
