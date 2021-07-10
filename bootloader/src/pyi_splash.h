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

#ifndef PYI_SPLASH_H
#define PYI_SPLASH_H

#include "zlib.h"
#include "pyi_global.h"
#include "pyi_archive.h"
#include "pyi_splashlib.h"

/* Archive item header for splash data
 * This struct is a header describing the rest of this archive item */
typedef struct _splash_data_header {
    /*
     * The filenames of the tcl and tk dynamic libraries. These
     * files are extracted into a subdirectory named after the name in
     * "rundir". This prevents the an error of "file already exists".
     */
    char tcl_libname[16];  /* Filename of tcl library, e.g. tcl86t.dll */
    char tk_libname[16];   /* Filename of tk library, e.g. tk86t.dll */
    char tk_lib[16];       /* Tk library root , e.g. "tk/" */
    char rundir[16];       /* temp folder inside extraction path
                            * in which the dependencies are extracted */

    int script_len;        /* Length of the script */
    int script_offset;     /* Offset (rel to start) of the script */

    int image_len;         /* Length of the image data */
    int image_offset;      /* Offset (rel to start) of the image */
    /*
     * To only extract the necessary files from the archive,
     * those fields describe an array of strings. Each string is
     * null-terminated and aligned after each other.
     */
    int requirements_len;
    int requirements_offset;
    /*
     * Followed by a chunk of data, including the splash screen
     * script,the image and the required files array.
     */

} SPLASH_DATA_HEADER;

/* Runtime status for the splash screen */
typedef struct _splash_status {
    /*
     * The Tcl interpreter in which the splash screen will run.
     * Threaded Tcl locks a interpreter to its thread which created
     * it and because we need to run the interpreter in a different
     * thread than python and the bootloader, this field is set
     * from a secondary thread. To not get into any hustles before using
     * the interpreter check via the thread_id if the current thread
     * is allowed to use the interpreter, if not use other methods.
     */
    Tcl_Interp *interp;
    /*
     * We only support threaded tcl. To identify on which thread
     * the status is currently accessed we store a unique identifier
     * for the thread in which the interpreter runs.
     *
     * On Windows:
     *  CPython commonly distributes a threaded version of tcl/tk, since
     *  a builtin module of tcl requires to be threaded (winsocks). We
     *  use that module to communicate with the python interpreter.
     *
     * On MacOs:
     *  As CPython/Mac/BuildScript/build-installer.py defines the
     *  --enable-threads flag is set for tcl/tk building, Python on MacOS
     *  probably comes with a threaded version.
     */
    Tcl_ThreadId thread_id;
    /*
     * Store the paths of the the libraries.
     * The values of these fields are either relative to the executable
     * or absolute.
     *
     * In onedir mode the paths are relative to the executable inside
     * the distribution folder. We assume onedir mode as long
     * pyi_splash_extract wasn't called-
     *
     * In onefile mode the paths are absolute values, pointing into
     * the temp directory.
     */
    char tcl_libpath[PATH_MAX];
    char tk_libpath[PATH_MAX];
    char tk_lib[PATH_MAX];
    char rundir[PATH_MAX];
    /*
     * The Tcl script to be executed to create the splash screen
     * and IPC mechanism
     */
    char *script;
    int   script_len;
    /*
     * Image to be show on the splash screen.
     * The image pointer will eventually be NULL, because it is only kept
     * till the interpreter is fully setup and copied the image data into
     * an buffer owned by it.
     */
    void *image;
    int   image_len;
    /*
     * To start tcl/tk some file have to be on the filesystem.
     * These fields describe an array of null-terminated strings. Those
     * strings are the filenames like those in the CArchive, listing all
     * files from the archive which have to be extracted before the
     * interpreter can be started.
     */
    char *requirements;
    int   requirements_len;
    /*
     * Flag if tcl and tk libraries were loaded. This indicate if it is safe
     * to call functions from Tcl/Tk. If the binaries are missing the splash
     * screen cannot be shown.
     */
    bool is_tcl_loaded;
    bool is_tk_loaded;
    /*
     * Keep the handles to the shared library, in order to close
     * them at finalization.
     */
    dylib_t dll_tcl;
    dylib_t dll_tk;

} SPLASH_STATUS;

typedef int (pyi_splash_event_proc)(SPLASH_STATUS *, void *);

/**
 * Public API functions for pyi_splash
 */
int pyi_splash_setup(SPLASH_STATUS *splash_status, ARCHIVE_STATUS *archive_status,
                     SPLASH_DATA_HEADER *data_header);
int pyi_splash_attach(SPLASH_STATUS *status);
int pyi_splash_finalize(SPLASH_STATUS *status);
int pyi_splash_start(SPLASH_STATUS *status, const char *executable);

/* Archive helper functions */
SPLASH_DATA_HEADER *pyi_splash_find(ARCHIVE_STATUS *status);
int pyi_splash_extract(ARCHIVE_STATUS *archive_status, SPLASH_STATUS *splash_status);

int pyi_splash_send(SPLASH_STATUS *status, bool async, void *user_data,
                    pyi_splash_event_proc proc);
int pyi_splash_update_prg(SPLASH_STATUS *status, TOC *ptoc);

/* Memory allocation functions */
SPLASH_STATUS *pyi_splash_status_new();
void pyi_splash_status_free(SPLASH_STATUS **splash_status);

#endif  /*PYI_SPLASH_H */
