/*
 * Bootloader for a packed executable.
 * Copyright (C) 2009, Lorenzo Masini
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
#include "getpath.h"
#include <sys/wait.h>

int append2enviroment(const char *name, const char *value);

void init_launcher(void)
{
}

int get_thisfile(char *thisfile, const char *programname)
{
    /* fill in thisfile */
#ifdef __CYGWIN__
    if (strncasecmp(&programname[strlen(argv[0])-4], ".exe", 4)) {
        strcpy(thisfile, programname);
        strcat(thisfile, ".exe");
        PI_SetProgramName(thisfile);
    }
    else
#endif
    PI_SetProgramName(programname);
    strcpy(thisfile, PI_GetProgramFullPath());
    VS("thisfile is %s\n", thisfile);
    
    return 0;
}

void get_homepath(char *homepath, const char *thisfile)
{
    /* fill in here (directory of thisfile) */
    strcpy(homepath, PI_GetPrefix());
    strcat(homepath, "/");
    VS("homepath is %s\n", homepath);
}

void get_archivefile(char *archivefile, const char *thisfile)
{
    strcpy(archivefile, thisfile);
    strcat(archivefile, ".pkg");
}

int append2enviroment(const char *name, const char *value)
{
    char *envvar;
    char *old_envvar;
    int nchars;

    old_envvar = getenv(name);

    nchars = strlen(value);
    if (old_envvar)
        nchars += strlen(old_envvar) + 1;

    /* at process exit: no need to free */
    envvar = (char*)malloc((nchars+1)*sizeof(char));
    if (envvar==NULL) {
            fprintf(stderr,"Cannot allocate memory for %s "
                           "environment variable\n", name);
            return -1;
    }

    strcpy(envvar, value);
    if (old_envvar) {
        strcat(envvar, ":");
        strcat(envvar, old_envvar);
    }
    setenv(name, envvar, 1);
    VS("%s\n", envvar);
    
    return 0;
}

int set_enviroment(const ARCHIVE_STATUS *status)
{
    int rc = 0;

    /* add temppath to LD_LIBRARY_PATH */
    if (status->temppath[0] != 0){
        rc = append2enviroment("LD_LIBRARY_PATH", status->temppath);
#ifdef __APPLE__
        /* add temppath to DYLD_LIBRARY_PATH */
        rc = append2enviroment("DYLD_LIBRARY_PATH", status->temppath);
#endif
    }
    rc = append2enviroment("LD_LIBRARY_PATH", status->homepath);
#ifdef __APPLE__
        /* add homepath to DYLD_LIBRARY_PATH */
    rc = append2enviroment("DYLD_LIBRARY_PATH", status->homepath);
#endif

    return rc;
}

int spawn(const char *thisfile, char *const argv[])
{
    pid_t pid = 0;
    int rc = 0;

    pid = fork();
    if (pid == 0)
        execvp(thisfile, argv);
    wait(&rc);
    
    return WEXITSTATUS(rc);
}
