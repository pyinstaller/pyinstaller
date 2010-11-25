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

// To call TransformProcessType in the child process
#if defined(__APPLE__) && defined(WINDOWED)
#include "Processes.h"
#endif

void exportWorkpath(char *workpath, char *envvar_name)
{
    char *envvar;
    char *old_envvar;
    int nchars;

    old_envvar = getenv(envvar_name);

    nchars = strlen(workpath);
    if (old_envvar)
        nchars += strlen(old_envvar) + 1;

    /* at process exit: no need to free */
    envvar = (char*)malloc((nchars+1)*sizeof(char));
    if (envvar==NULL) {
            fprintf(stderr,"Cannot allocate memory for %s "
                           "environment variable\n",envvar_name);
            exit(2);
    }

    strcpy(envvar,workpath);
    if (old_envvar) {
        strcat(envvar, ":");
        strcat(envvar, old_envvar);
    }
    setenv(envvar_name, envvar, 1);
    VS("%s\n", envvar);
}

int main(int argc, char* argv[])
{
    char thisfile[_MAX_PATH];
    char homepath[_MAX_PATH];
    char archivefile[_MAX_PATH + 5];
    TOC *ptoc = NULL;
    int rc = 0;
    int pid;
    char *workpath = NULL;
    /* atexit(cleanUp); */

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

    workpath = getenv( "_MEIPASS2" );
    VS("_MEIPASS2 (workpath) is %s\n", (workpath ? workpath : "NULL"));

    /* fill in here (directory of thisfile) */
    strcpy(homepath, PI_GetPrefix());
    strcat(homepath, "/");
    VS("homepath is %s\n", homepath);

    if (init(homepath, &thisfile[strlen(homepath)], workpath)) {
        /* no pkg there, so try the nonelf configuration */
        strcpy(archivefile, thisfile);
        strcat(archivefile, ".pkg");
        if (init(homepath, &archivefile[strlen(homepath)], workpath)) {
            FATALERROR("Cannot open self %s or archive %s\n",
                    thisfile, archivefile);
            return -1;
        }
    }

    if (workpath) {
        /* we're the "child" process */
#if defined(__APPLE__) && defined(WINDOWED)
        ProcessSerialNumber psn = { 0, kCurrentProcess };
        OSStatus returnCode = TransformProcessType(&psn, kProcessTransformToForegroundApplication);
#endif
        VS("Already have a workpath - running!\n");
        rc = doIt(argc, argv);
    }
    else {
        if (extractBinaries(&workpath)) {
            VS("Error extracting binaries\n");
            return -1;
        }

        if (workpath == NULL)
            workpath = homepath;

        VS("Executing self as child with ");
        /* run the "child" process, then clean up */
        setenv("_MEIPASS2", workpath, 1);

        /* add workpath to LD_LIBRARY_PATH */
        exportWorkpath(workpath, "LD_LIBRARY_PATH");
#ifdef __APPLE__
        /* add workpath to DYLD_LIBRARY_PATH */
        exportWorkpath(workpath, "DYLD_LIBRARY_PATH");
#endif
        pid = fork();
        if (pid == 0)
            execvp(thisfile, argv);
        wait(&rc);
        rc = WEXITSTATUS(rc);

        VS("Back to parent...\n");
        if (strcmp(workpath, homepath) != 0)
            clear(workpath);
    }
    return rc;
}
