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


#define MAX_STATUS_LIST 20


#if defined(WIN32) && defined(WINDOWED)
int APIENTRY WinMain( HINSTANCE hInstance, HINSTANCE hPrevInstance,
						LPSTR lpCmdLine, int nCmdShow )
#else
int main(int argc, char* argv[])
#endif
{
    /*  status_list[0] is reserved for the main process, the others for dependencies. */
    ARCHIVE_STATUS *status_list[MAX_STATUS_LIST];
    char executable[PATH_MAX];
    char homepath[PATH_MAX];
    char archivefile[PATH_MAX + 5];
    char MEIPASS2[PATH_MAX + 1];
    int rc = 0;
    char *extractionpath = NULL;
#if defined(WIN32) && defined(WINDOWED)
    int argc = __argc;
    char **argv = __argv;
#endif
    int i = 0;

    memset(&status_list, 0, MAX_STATUS_LIST * sizeof(ARCHIVE_STATUS *));
    if ((status_list[SELF] = (ARCHIVE_STATUS *) calloc(1, sizeof(ARCHIVE_STATUS))) == NULL){
        FATALERROR("Cannot allocate memory for ARCHIVE_STATUS\n");
        return -1;
    }

    pyi_path_executable(executable, argv[0]);
    pyi_path_archivefile(archivefile, executable);
    pyi_path_homepath(homepath, executable);

    extractionpath = pyi_getenv("_MEIPASS2");

    VS("_MEIPASS2 is %s\n", (extractionpath ? extractionpath : "NULL"));

    if (pyi_arch_setup(status_list[SELF], homepath, &executable[strlen(homepath)])) {
        if (pyi_arch_setup(status_list[SELF], homepath, &archivefile[strlen(homepath)])) {
            FATALERROR("Cannot open self %s or archive %s\n",
                    executable, archivefile);
            return -1;
        }
    }

#ifdef WIN32
    /* On Windows use single-process for --onedir mode. */
    if (!extractionpath && !needToExtractBinaries(status_list)) {
        VS("No need to extract files to run; setting extractionpath to homepath\n");
        extractionpath = homepath;
        strcpy(MEIPASS2, homepath);
        pyi_setenv("_MEIPASS2", MEIPASS2); //Bootstrap sets sys._MEIPASS, plugins rely on it
    }
#endif
    if (extractionpath) {
        VS("Already in the child - running!\n");
        /*  If binaries were extracted to temppath,
         *  we pass it through status variable
         */
        if (strcmp(homepath, extractionpath) != 0) {
            strcpy(status_list[SELF]->temppath, extractionpath);
            /*
             * Temp path exits - set appropriate flag and change
             * status->mainpath to point to temppath.
             */
            status_list[SELF]->has_temp_directory = true;
            strcpy(status_list[SELF]->mainpath, status_list[SELF]->temppath);
        }

        pyi_launch_initialize(executable, extractionpath);
        rc = pyi_launch_execute(status_list[SELF], argc, argv);
        pyi_launch_finalize();

    } else {
        /* status->temppath is created if necessary. */
        if (extractBinaries(status_list)) {
            VS("temppath is %s\n", status_list[SELF]->temppath);
            VS("Error extracting binaries\n");
            return -1;
        }

        VS("Executing self as child with ");
        /* Run the 'child' process, then clean up. */
        pyi_setenv("_MEIPASS2", status_list[SELF]->temppath[0] != 0 ? status_list[SELF]->temppath : homepath);

        if (pyi_utils_set_environment(status_list[SELF]) == -1)
            return -1;

        rc = pyi_utils_create_child(executable, argv);

        VS("Back to parent...\n");
        if (status_list[SELF]->has_temp_directory == true)
            pyi_remove_temp_path(status_list[SELF]->temppath);

        for (i = SELF; status_list[i] != NULL; i++) {
            VS("Freeing status for %s\n", status_list[i]->archivename);
            free(status_list[i]);
        }
    }
    return rc;
}
