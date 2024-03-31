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
    /*
     * The filenames of the Tcl and Tk shared libraries. In onefile
     * mode, these files extracted into a sub-directory named after
     * the name in "rundir". This prevents the "file already exists"
     * error when main onefile extraction takes place.
     */

    /* Filename of the Tcl shared library, e.g., tcl86t.dll */
    char tcl_libname[16];

    /* Filename of the Tk shared library, e.g. tk86t.dll */
    char tk_libname[16];

    /* Tk module library root, e.g. "tk/" */
    char tk_lib[16];

    /* Name of the temporary directory inside the onefile extraction
     * path, into which splash dependencies are extracted when running
     * in onefile mode. */
    char rundir[16];

    /* Splash screen script */
    int script_len;
    int script_offset;

    /* Image data */
    int image_len;
    int image_offset;

    /*
     * To only extract the necessary files from the archive, the following
     * two fields define an array of strings. Strings are NULL-terminated
     * and stored one after another.
     */
    int requirements_len;
    int requirements_offset;

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
     *
     * In onedir mode, these are located in the top-level application
     * directory.
     *
     * In onefile mode, they are extracted to sub-directory of the top-level
     * application directory (an ephemeral temporary directory). The name
     * of this sub-directory is controlled by the `rundir` field in the
     * splash header.
     *
     * The `splash_dependencies_dir` contains full path to either application's
     * top-level directory, or sub-directory under it. All other paths
     * (`tcl_libpath`, `tk_libpath`, `tk_lib` are full paths that are
     * rooted in `splash_dependencies_dir`. */
    char splash_dependencies_dir[PATH_MAX];
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

int pyi_splash_send(
    SPLASH_CONTEXT *splash,
    bool async,
    const void *user_data,
    pyi_splash_event_proc proc
);
int pyi_splash_update_prg(SPLASH_CONTEXT *splash, const TOC *toc_entry);

/* Memory allocation functions */
SPLASH_CONTEXT *pyi_splash_context_new();
void pyi_splash_context_free(SPLASH_CONTEXT **splash_ref);

#endif  /*PYI_SPLASH_H */
