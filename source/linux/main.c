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
#include "launch.h"

#ifdef FREEZE_EXCEPTIONS
extern unsigned char M_exceptions[];
static struct _frozen _PyImport_FrozenModules[] = {
    {"exceptions", M_exceptions, EXCEPTIONS_LEN},
    {0, 0, 0}
};
#endif
int main(int argc, char* argv[])
{
    char thisfile[_MAX_PATH];
    char homepath[_MAX_PATH];
    char magic_envvar[_MAX_PATH + 12];
    char ldlib_envvar[_MAX_PATH * 4 + 12];
    char archivefile[_MAX_PATH + 5];
    char *oldldlib;
    TOC *ptoc = NULL;
    int rc = 0;
    char *workpath = NULL;
    /* atexit(cleanUp); */
#ifdef FREEZE_EXCEPTIONS
    PyImport_FrozenModules = _PyImport_FrozenModules;
#endif
    // fill in thisfile
#ifdef __CYGWIN__
    if (strncasecmp(&argv[0][strlen(argv[0])-4], ".exe", 4)) {
        strcpy(thisfile, argv[0]);
        strcat(thisfile, ".exe");
        Py_SetProgramName(thisfile);
    }
    else 
#endif
        Py_SetProgramName(argv[0]);
    strcpy(thisfile, Py_GetProgramFullPath());
    VS(thisfile);
    VS(" is thisfile\n");
    
    workpath = getenv( "_MEIPASS2" );
    VS(workpath);
    VS(" is _MEIPASS2 (workpath)\n");

    // fill in here (directory of thisfile)
    strcpy(homepath, Py_GetPrefix());
    strcat(homepath, "/");
    VS(homepath);
    VS(" is homepath\n");

    if (init(homepath, &thisfile[strlen(homepath)], workpath)) {
        /* no pkg there, so try the nonelf configuration */
        strcpy(archivefile, thisfile);
        strcat(archivefile, ".pkg");
        if (init(homepath, &archivefile[strlen(homepath)], workpath)) {
            FATALERROR("Cannot open self ");
            FATALERROR(thisfile);
            FATALERROR(" or archive ");
            FATALERROR(archivefile);
            FATALERROR("\n");
            return -1;
        }
    }

    if (workpath) {
        // we're the "child" process
        VS("Already have a workpath - running!\n");
        rc = doIt(argc, argv);
        if (strcmp(workpath, homepath)!=0)
            clear(workpath);
    }
    else {
        if (extractBinaries(&workpath)) {
            VS("Error extracting binaries\n");
            return -1;
        }
        if (workpath == NULL) {
            /* now look for the "force LD_LIBRARY" flag */
            ptoc = getFirstTocEntry();
            while (ptoc) {
                if ((ptoc->typcd == 'o') && (ptoc->name[0] == 'f'))
                    workpath = homepath;
                    ptoc = getNextTocEntry(ptoc);
                }
        }
        if (workpath) {
            VS("Executing self as child with ");
            // run the "child" process, then clean up
            strcpy(magic_envvar, "_MEIPASS2=");
            strcat(magic_envvar, workpath);
            putenv(magic_envvar);
            // now LD_LIBRARY_PATH
            strcpy(ldlib_envvar, "LD_LIBRARY_PATH=");
            strcat(ldlib_envvar, workpath);
            ldlib_envvar[strlen(ldlib_envvar)-1] = '\0';
            oldldlib = getenv("LD_LIBRARY_PATH");
            if (oldldlib) {
                strcat(ldlib_envvar, ":");
                strcat(ldlib_envvar, oldldlib);
            }
            putenv(ldlib_envvar);
            VS(ldlib_envvar);
            VS("\n");
            rc = execvp(thisfile, argv);
            VS("Back to parent...\n");
        }
        else
            // no "child" process necessary
            rc = doIt(argc, argv);
    }
    return rc;
}
