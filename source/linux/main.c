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
#include "getpath.h"
#include <sys/wait.h>

#ifdef FREEZE_EXCEPTIONS
extern unsigned char M_exceptions[];
static struct _frozen _PyImport_FrozenModules[] = {
    {"exceptions", M_exceptions, EXCEPTIONS_LEN},
    {0, 0, 0}
};
#endif

void exportExtractionPath(char *extractionpath, char *envvar_name)
{
    char *envvar;
    char *old_envvar;
    int nchars;

    old_envvar = getenv(envvar_name);

    nchars = strlen(extractionpath);
    if (old_envvar)
        nchars += strlen(old_envvar) + 1;

    /* at process exit: no need to free */
    envvar = (char*)malloc((nchars+1)*sizeof(char));
    if (envvar==NULL) {
            fprintf(stderr,"Cannot allocate memory for %s "
                           "environment variable\n",envvar_name);
            exit(2);
    }

    strcpy(envvar, extractionpath);
    if (old_envvar) {
        strcat(envvar, ":");
        strcat(envvar, old_envvar);
    }
    setenv(envvar_name, envvar, 1);
    VS("%s\n", envvar);
}

int main(int argc, char* argv[])
{
    ARCHIVE_STATUS status;
    memset(&status, 0, sizeof(ARCHIVE_STATUS));
    char thisfile[_MAX_PATH];
    char homepath[_MAX_PATH];
    char archivefile[_MAX_PATH + 5];
    TOC *ptoc = NULL;
    int rc = 0;
    int pid;
    char *extractionpath = NULL;
    /* atexit(cleanUp); */
#ifdef FREEZE_EXCEPTIONS
    PyImport_FrozenModules = _PyImport_FrozenModules;
#endif
    /* fill in thisfile */
#ifdef __CYGWIN__
    if (strncasecmp(&argv[0][strlen(argv[0])-4], ".exe", 4)) {
        strcpy(thisfile, argv[0]);
        strcat(thisfile, ".exe");
        PI_SetProgramName(thisfile);
    }
    else
#endif
    PI_SetProgramName(argv[0]);
    strcpy(thisfile, PI_GetProgramFullPath());
    VS("thisfile is %s\n", thisfile);

    extractionpath = getenv( "_MEIPASS2" );
    VS("_MEIPASS2 is %s\n", (extractionpath ? extractionpath : "NULL"));

    /* fill in here (directory of thisfile) */
    strcpy(homepath, PI_GetPrefix());
    strcat(homepath, "/");
    VS("homepath is %s\n", homepath);

    if (init(&status, homepath, &thisfile[strlen(homepath)])) {
        /* no pkg there, so try the nonelf configuration */
        strcpy(archivefile, thisfile);
        strcat(archivefile, ".pkg");
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
        setenv("_MEIPASS2", status.temppath[0] != NULL ? status.temppath : homepath, 1);

        /* add temppath to LD_LIBRARY_PATH */
        if (status.temppath[0] != NULL){
            exportExtractionPath(status.temppath, "LD_LIBRARY_PATH");
#ifdef __APPLE__
        /* add temppath to DYLD_LIBRARY_PATH */
            exportExtractionPath(status.temppath, "DYLD_LIBRARY_PATH");
#endif
        }
        exportExtractionPath(homepath, "LD_LIBRARY_PATH");
#ifdef __APPLE__
        /* add homepath to DYLD_LIBRARY_PATH */
        exportExtractionPath(homepath, "DYLD_LIBRARY_PATH");
#endif
        pid = fork();
        if (pid == 0)
            execvp(thisfile, argv);
        wait(&rc);
        rc = WEXITSTATUS(rc);

        VS("Back to parent...\n");
        if (status.temppath[0] != NULL)        
            clear(status.temppath);
    }
    return rc;
}

