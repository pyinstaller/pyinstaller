/*
 * Bootloader for a packed executable.
 * Copyright (C) 2005-2011, Giovanni Bajo
 * Based on previous work under copyright (c) 2002 McMillan Enterprises, Inc.
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; either version 2
 * of the License, or (at your option) any later version.
 *
 * In addition to the permissions in the GNU General Public License, the
 * authors give you unlimited permission to link or embed the compiled
 * version of this file into combinations with other programs, and to
 * distribute those combinations without any restriction coming from the
 * use of this file. (The General Public License restrictions do apply in
 * other respects; for example, they cover modification of the file, and
 * distribution when not linked into a combine executable.)
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA
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


/* To call TransformProcessType in the child process. */
#if defined(__APPLE__) && defined(WINDOWED)
#include <Carbon/Carbon.h>
#endif

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
#include "pyi_global.h"
#include "pyi_archive.h"
#include "pyi_utils.h"
#include "pyi_pythonlib.h"
#include "utils.h"
#include "launch.h"


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
    char thisfile[PATH_MAX];
#ifdef WIN32
    wchar_t thisfilew[PATH_MAX + 1];
#endif
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

    get_thisfile(thisfile, argv[0]);
#ifdef WIN32
    get_thisfilew(thisfilew);
#endif
    get_archivefile(archivefile, thisfile);
    get_homepath(homepath, thisfile);

    extractionpath = pyi_getenv("_MEIPASS2");

    /* If the Python program we are about to run invokes another PyInstaller
     * one-file program as subprocess, this subprocess must not be fooled into
     * thinking that it is already unpacked. Therefore, PyInstaller deletes
     * the _MEIPASS2 variable from the environment in _pyi_bootstrap.py.
     *
     * However, on some platforms (e.g. AIX) the Python function 'os.unsetenv()'
     * does not always exist. In these cases we cannot delete the _MEIPASS2
     * environment variable from Python but only set it to the empty string.
     * The code below takes into account that _MEIPASS2 may exist while its
     * value is only the empty string.
     */
    if (extractionpath && *extractionpath == 0) {
        extractionpath = NULL;
    }

    VS("_MEIPASS2 is %s\n", (extractionpath ? extractionpath : "NULL"));

    if (init(status_list[SELF], homepath, &thisfile[strlen(homepath)])) {
        if (init(status_list[SELF], homepath, &archivefile[strlen(homepath)])) {
            FATALERROR("Cannot open self %s or archive %s\n",
                    thisfile, archivefile);
            return -1;
        }
    }

#ifdef WIN32
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
#ifdef WIN32
            strcpy(status_list[SELF]->temppathraw, extractionpath);
#endif
            /*
             * Temp path exits - set appropriate flag and change
             * status->mainpath to point to temppath.
             */
            status_list[SELF]->has_temp_directory = true;
#ifdef WIN32
            strcpy(status_list[SELF]->mainpath, status_list[SELF]->temppathraw);
#else
            strcpy(status_list[SELF]->mainpath, status_list[SELF]->temppath);
#endif
        }

#if defined(__APPLE__) && defined(WINDOWED)
        ProcessSerialNumber psn = { 0, kCurrentProcess };
        OSStatus returnCode = TransformProcessType(&psn, kProcessTransformToForegroundApplication);
#endif
#ifdef WIN32
        CreateActContext(extractionpath, thisfile);
#endif
        rc = doIt(status_list[SELF], argc, argv);
#ifdef WIN32
        ReleaseActContext();
#endif
	pyi_pylib_finalize();
    } else {
        if (extractBinaries(status_list)) {
            VS("Error extracting binaries\n");
            return -1;
        }

        VS("Executing self as child with ");
        /* run the "child" process, then clean up */
#ifdef WIN32
        pyi_setenv("_MEIPASS2", status_list[SELF]->temppath[0] != 0 ? status_list[SELF]->temppathraw : status_list[SELF]->homepathraw);
#else
        pyi_setenv("_MEIPASS2", status_list[SELF]->temppath[0] != 0 ? status_list[SELF]->temppath : homepath);
#endif

        if (set_environment(status_list[SELF]) == -1)
            return -1;

#ifndef WIN32
        rc = spawn(thisfile, argv);
#else
        rc = spawn(thisfilew);
#endif

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
