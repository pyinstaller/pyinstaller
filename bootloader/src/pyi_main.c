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

/*
 * Bootloader for a packed executable.
 */

#ifdef _WIN32
    #include <windows.h>
    #include <wchar.h>
#endif
#include <stdio.h>  /* FILE */
#include <stdlib.h> /* calloc */
#include <string.h> /* memset */

#if defined(__linux__)
    #include <sys/prctl.h> /* prctl() */
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

int
pyi_main(int argc, char * argv[])
{
    /*  archive_status contain status information of the main process. */
    ARCHIVE_STATUS *archive_status = NULL;
    char executable[PATH_MAX];
    char homepath[PATH_MAX];
    char archivefile[PATH_MAX];
    int rc = 0;
    char *extractionpath = NULL;

#if defined(__linux__)
    char *processname = NULL;
#endif  /* defined(__linux__) */

#ifdef _MSC_VER
    /* Visual C runtime incorrectly buffers stderr */
    setbuf(stderr, (char *)NULL);
#endif  /* _MSC_VER */

    VS("PyInstaller Bootloader 3.x\n");

    archive_status = pyi_arch_status_new(archive_status);
    if (archive_status == NULL) {
        return -1;
    }
    if ((! pyi_path_executable(executable, argv[0])) ||
        (! pyi_path_archivefile(archivefile, executable)) ||
        (! pyi_path_homepath(homepath, executable))) {
        return -1;
    }

    /* For the curious:
     * On Windows, the UTF-8 form of MEIPASS2 is passed to pyi_setenv, which
     * decodes to UTF-16 before passing it to the Windows API. So the var's value
     * is full unicode.
     *
     * On OS X/Linux, the MEIPASS2 value is passed as the bytes received from the OS.
     * Only Python will care about its encoding, and it is passed to Python using
     * PyUnicode_DecodeFSDefault.
     */

    extractionpath = pyi_getenv("_MEIPASS2");

    /* If the Python program we are about to run invokes another PyInstaller
     * one-file program as subprocess, this subprocess must not be fooled into
     * thinking that it is already unpacked. Therefore, PyInstaller deletes
     * the _MEIPASS2 variable from the environment.
     */

    pyi_unsetenv("_MEIPASS2");

    VS("LOADER: _MEIPASS2 is %s\n", (extractionpath ? extractionpath : "NULL"));

    if ((! pyi_arch_setup(archive_status, executable)) &&
        (! pyi_arch_setup(archive_status, archivefile))) {
            FATALERROR("Cannot open self %s or archive %s\n",
                       executable, archivefile);
            return -1;
    }

#if defined(__linux__)

    /* Set process name on linux. The environment variable is set by
       parent launcher process. */
    processname = pyi_getenv("_PYI_PROCNAME");
    if (processname) {
        VS("LOADER: restoring linux process name from _PYI_PROCNAME: %s\n", processname);
        if (prctl(PR_SET_NAME, processname, 0, 0)) {
            FATALERROR("LOADER: failed to set linux process name!\n");
            return -1;
        }
        free(processname);
    }
    pyi_unsetenv("_PYI_PROCNAME");

#endif  /* defined(__linux__) */

    /* These are used only in pyi_pylib_set_sys_argv, which converts to wchar_t */
    archive_status->argc = argc;
    archive_status->argv = argv;

#if defined(_WIN32) || defined(__APPLE__)

    /* On Windows and Mac use single-process for --onedir mode. */
    if (!extractionpath && !pyi_launch_need_to_extract_binaries(archive_status)) {
        VS("LOADER: No need to extract files to run; setting extractionpath to homepath\n");
        extractionpath = homepath;
    }

#endif

#ifdef _WIN32

    if (extractionpath) {
        /* Add extraction folder to DLL search path */
        wchar_t * dllpath_w;
        dllpath_w = pyi_win32_utils_from_utf8(NULL, extractionpath, 0);
        SetDllDirectory(dllpath_w);
        VS("LOADER: SetDllDirectory(%s)\n", extractionpath);
        free(dllpath_w);
    }
#endif /* ifdef _WIN32 */

    if (extractionpath) {
        VS("LOADER: Already in the child - running user's code.\n");

        /*  If binaries were extracted to temppath,
         *  we pass it through status variable
         */
        if (strcmp(homepath, extractionpath) != 0) {
            if (snprintf(archive_status->temppath, PATH_MAX,
                         "%s", extractionpath) >= PATH_MAX) {
                VS("LOADER: temppath exceeds PATH_MAX\n");
                return -1;
            }
            /*
             * Temp path exits - set appropriate flag and change
             * status->mainpath to point to temppath.
             */
            archive_status->has_temp_directory = true;
            strcpy(archive_status->mainpath, archive_status->temppath);
        }

        /* Main code to initialize Python and run user's code. */
        pyi_launch_initialize(archive_status);
        rc = pyi_launch_execute(archive_status);
        pyi_launch_finalize(archive_status);

    }
    else {
#if defined(__linux__)
        char tmp_processname[16]; /* 16 bytes as per prctl() man page */
#endif  /* defined(__linux__) */

        /* status->temppath is created if necessary. */
        if (pyi_launch_extract_binaries(archive_status)) {
            VS("LOADER: temppath is %s\n", archive_status->temppath);
            VS("LOADER: Error extracting binaries\n");
            return -1;
        }

        /* Run the 'child' process, then clean up. */

        VS("LOADER: Executing self as child\n");
        pyi_setenv("_MEIPASS2",
                   archive_status->temppath[0] !=
                   0 ? archive_status->temppath : homepath);

        VS("LOADER: set _MEIPASS2 to %s\n", pyi_getenv("_MEIPASS2"));

#if defined(__linux__)

        /* Pass the process name to child via environment variable. */
        if (!prctl(PR_GET_NAME, tmp_processname, 0, 0)) {
            VS("LOADER: linux: storing process name into _PYI_PROCNAME: %s\n", tmp_processname);
            pyi_setenv("_PYI_PROCNAME", tmp_processname);
        }

#endif  /* defined(__linux__) */

        if (pyi_utils_set_environment(archive_status) == -1) {
            return -1;
        }

        /* Transform parent to background process on OSX only. */
        pyi_parent_to_background();

        /* Run user's code in a subprocess and pass command line arguments to it. */
        rc = pyi_utils_create_child(executable, archive_status, argc, argv);

        VS("LOADER: Back to parent (RC: %d)\n", rc);

        VS("LOADER: Doing cleanup\n");

        if (archive_status->has_temp_directory == true) {
            pyi_remove_temp_path(archive_status->temppath);
        }
        pyi_arch_status_free(archive_status);

    }
    return rc;
}
