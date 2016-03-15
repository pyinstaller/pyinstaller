/*
 * ****************************************************************************
 * Copyright (c) 2013-2016, PyInstaller Development Team.
 * Distributed under the terms of the GNU General Public License with exception
 * for distributing bootloader.
 *
 * The full license is in the file COPYING.txt, distributed with this software.
 * ****************************************************************************
 */

/*
 * Bootloader for a packed executable.
 */

/* TODO: use safe string functions */
#define _CRT_SECURE_NO_WARNINGS 1

#ifdef _WIN32
    #include <windows.h>
    #include <wchar.h>
#else
    #include <limits.h>  /* PATH_MAX */
#endif
#include <stdio.h>  /* FILE */
#include <stdlib.h> /* calloc */
#include <string.h> /* memset */

/* PyInstaller headers. */
#include "pyi_global.h"  /* PATH_MAX for win32 */
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
    wchar_t * dllpath_w;

    int i = 0;

#ifdef _MSC_VER
    /* Visual C runtime incorrectly buffers stderr */
    setbuf(stderr, (char *)NULL);
#endif  /* _MSC_VER */

    VS("PyInstaller Bootloader 3.x\n");

    /* TODO create special function to allocate memory for archive status pyi_arch_status_alloc_memory(archive_status); */
    archive_status = (ARCHIVE_STATUS *) calloc(1, sizeof(ARCHIVE_STATUS));

    if (archive_status == NULL) {
        FATALERROR("Cannot allocate memory for ARCHIVE_STATUS\n");
        return -1;

    }

    pyi_path_executable(executable, argv[0]);
    pyi_path_archivefile(archivefile, executable);
    pyi_path_homepath(homepath, executable);

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

    if (pyi_arch_setup(archive_status, homepath, &executable[strlen(homepath)])) {
        if (pyi_arch_setup(archive_status, homepath, &archivefile[strlen(homepath)])) {
            FATALERROR("Cannot open self %s or archive %s\n",
                       executable, archivefile);
            return -1;
        }
    }

    /* These are used only in pyi_pylib_set_sys_argv, which converts to wchar_t */
    archive_status->argc = argc;
    archive_status->argv = argv;

#ifdef _WIN32

    /* On Windows use single-process for --onedir mode. */
    if (!extractionpath && !pyi_launch_need_to_extract_binaries(archive_status)) {
        VS("LOADER: No need to extract files to run; setting extractionpath to homepath\n");
        extractionpath = homepath;
    }

    if (extractionpath) {
        /* Add extraction folder to DLL search path */
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
            strcpy(archive_status->temppath, extractionpath);
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

        if (pyi_utils_set_environment(archive_status) == -1) {
            return -1;
        }

        /* Transform parent to background process on OSX only. */
        pyi_parent_to_background();

        /* Run user's code in a subprocess and pass command line arguments to it. */
        rc = pyi_utils_create_child(executable, argc, argv);

        VS("LOADER: Back to parent (RC: %d)\n", rc);

        VS("LOADER: Doing cleanup\n");

        if (archive_status->has_temp_directory == true) {
            pyi_remove_temp_path(archive_status->temppath);
        }
        pyi_arch_status_free_memory(archive_status);

    }
    return rc;
}
