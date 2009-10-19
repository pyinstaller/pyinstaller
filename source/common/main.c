/*
 * Bootloader for a packed executable.
 * Copyright (C) 2005, Giovanni Bajo
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
#include "utils.h"
#ifndef WIN32
#include <sys/wait.h>
#endif


#ifdef _CONSOLE
int main(int argc, char* argv[])
#else
int APIENTRY WinMain( HINSTANCE hInstance, HINSTANCE hPrevInstance,
						LPSTR lpCmdLine, int nCmdShow )
#endif
{
    ARCHIVE_STATUS status;
    char thisfile[_MAX_PATH];
#ifdef WIN32
    WCHAR thisfilew[_MAX_PATH + 1];
#endif
    char homepath[_MAX_PATH];
    char archivefile[_MAX_PATH + 5];
	char MEIPASS2[_MAX_PATH + 11] = "_MEIPASS2=";
    int rc = 0;
    char *extractionpath = NULL;
#ifndef _CONSOLE
	int argc = __argc;
	char **argv = __argv;
#endif
    memset(&status, 0, sizeof(ARCHIVE_STATUS));

    get_thisfile(thisfile, argv[0]);
#ifdef WIN32
	get_thisfilew(thisfilew);
#endif
    get_archivefile(archivefile, thisfile);
	get_homepath(homepath, thisfile);
	
    extractionpath = getenv( "_MEIPASS2" );
    VS("_MEIPASS2 is %s\n", (extractionpath ? extractionpath : "NULL"));

    if (init(&status, homepath, &thisfile[strlen(homepath)])) {
        if (init(&status, homepath, &archivefile[strlen(homepath)])) {
            FATALERROR("Cannot open self %s or archive %s\n",
                    thisfile, archivefile);
            return -1;
        }
    }

    if (extractionpath) {
        VS("Already in the child - running!\n");
        /*  If binaries where extracted to temppath, 
         *  we pass it through status variable 
         */
        if (strcmp(homepath, extractionpath) != 0) 
            strcpy(status.temppath, extractionpath);
        rc = doIt(&status, argc, argv);
    }
    else {
        if (extractBinaries(&status)) {
            VS("Error extracting binaries\n");
            return -1;
        }

        VS("Executing self as child with ");
        /* run the "child" process, then clean up */
		strcat(MEIPASS2, status.temppath[0] != 0 ? status.temppath : homepath);
		putenv(MEIPASS2);
		
        if (set_enviroment(&status) == -1)
            return -1;

#ifndef WIN32
        rc = spawn(thisfile, argv);
#else
		rc = spawn(thisfilew);
#endif

        VS("Back to parent...\n");
        if (status.temppath[0] != 0)        
            clear(status.temppath);
    }
    return rc;
}

