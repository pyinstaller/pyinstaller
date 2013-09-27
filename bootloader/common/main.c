/*
 * ****************************************************************************
 * Copyright (c) 2013, PyInstaller Development Team.
 * Distributed under the terms of the GNU General Public License with exception
 * for distributing bootloader.
 *
 * The full license is in the file COPYING.txt, distributed with this software.
 * ****************************************************************************
 */


/*
 * Bootloader for a packed executable.
 */


/* 
 * Use Sean's Tool Box -- public domain -- http://nothings.org/stb.h. 
 * 
 * This toolbox wraps some standard functions in a portable way and
 * contains some additional utility fuctions.
 * (string, file, utf8, etc.)
 *
 * All functions starting with 'stb_' prefix are from this toolbox.
 * To use this toolbox just do:
 *
 * #include "stb.h"
 */
#define STB_DEFINE 1
#define STB_NO_REGISTRY 1  // Disable registry functions.
#define STB_NO_STB_STRINGS 1  // Disable config read/write functions.

#define _CRT_SECURE_NO_WARNINGS 1


#ifdef WIN32
    #include <windows.h>
    #include <wchar.h>
#else
    #include <limits.h>  // PATH_MAX
#endif
#include <stdio.h>  // FILE
#include <stdlib.h>  // calloc
#include <string.h>  // memset


/* PyInstaller headers. */
#include "stb.h"
#include "pyi_global.h" // PATH_MAX for win32
#include "pyi_path.h"
#include "pyi_archive.h"
#include "pyi_utils.h"
#include "pyi_pythonlib.h"
#include "pyi_launch.h"



#if defined(WIN32) && defined(WINDOWED)
int APIENTRY WinMain( HINSTANCE hInstance, HINSTANCE hPrevInstance,
						LPSTR lpCmdLine, int nCmdShow )
#else
int main(int argc, char* argv[])
#endif
{
    /*  archive_status contain status information of the main process. */
    ARCHIVE_STATUS *archive_status = NULL;
    char executable[PATH_MAX];
    char homepath[PATH_MAX];
    char archivefile[PATH_MAX];
    char MEIPASS2[PATH_MAX];
    int rc = 0;
    char *extractionpath = NULL;
#if defined(WIN32) && defined(WINDOWED)
    int argc = __argc;
    char **argv = __argv;
#endif
    int i = 0;

    archive_status = (ARCHIVE_STATUS *) calloc(1,sizeof(ARCHIVE_STATUS));
    if (archive_status == NULL) {
        FATALERROR("Cannot allocate memory for ARCHIVE_STATUS\n");
        return -1;
    }

    pyi_path_executable(executable, argv[0]);
    pyi_path_archivefile(archivefile, executable);
    pyi_path_homepath(homepath, executable);

    extractionpath = pyi_getenv("_MEIPASS2");

    VS("LOADER: _MEIPASS2 is %s\n", (extractionpath ? extractionpath : "NULL"));

    if (pyi_arch_setup(archive_status, homepath, &executable[strlen(homepath)])) {
        if (pyi_arch_setup(archive_status, homepath, &archivefile[strlen(homepath)])) {
            FATALERROR("Cannot open self %s or archive %s\n",
                    executable, archivefile);
            return -1;
        }
    }

#ifdef WIN32
    /* On Windows use single-process for --onedir mode. */
    if (!extractionpath && !pyi_launch_need_to_extract_binaries(archive_status)) {
        VS("LOADER: No need to extract files to run; setting extractionpath to homepath\n");
        extractionpath = homepath;
        strcpy(MEIPASS2, homepath);
        pyi_setenv("_MEIPASS2", MEIPASS2); //Bootstrap sets sys._MEIPASS, plugins rely on it
    }
#endif
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
        pyi_launch_initialize(executable, extractionpath);
        rc = pyi_launch_execute(archive_status, argc, argv);
        pyi_launch_finalize(archive_status);

    } else {

        /* status->temppath is created if necessary. */
        if (pyi_launch_extract_binaries(archive_status)) {
            VS("LOADER: temppath is %s\n", archive_status->temppath);
            VS("LOADER: Error extracting binaries\n");
            return -1;
        }

        VS("LOADER: Executing self as child\n");
        /* Run the 'child' process, then clean up. */
        pyi_setenv("_MEIPASS2", archive_status->temppath[0] != 0 ? archive_status->temppath : homepath);

        VS("LOADER: set _MEIPASS2 to %s\n", pyi_getenv("_MEIPASS2"));

        if (pyi_utils_set_environment(archive_status) == -1)
            return -1;

        /* Run user's code in a subprocess and pass command line arguments to it. */
        rc = pyi_utils_create_child(executable, argc, argv);

        VS("LOADER: Back to parent\n");

        VS("LOADER: Doing cleanup\n");
        if (archive_status->has_temp_directory == true)
            pyi_remove_temp_path(archive_status->temppath);
        pyi_arch_status_free_memory(archive_status);
        if (extractionpath != NULL)
            free(extractionpath);
    }
    return rc;
}
