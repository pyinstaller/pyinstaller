/*
 * Some Linux/Unix utility functions.
 *
 * Copyright (C) 2012, Martin Zibricky
 * Copyright (C) 2009, Lorenzo Masini
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


#include <limits.h>
#include <signal.h>
#include <stddef.h>  // ptrdiff_t
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>


/* PyInstaller headers. */
#include "stb.h"
#include "pyi_global.h"
#include "pyi_archive.h"
// TODO Eliminate getpath.c/.h and replace it with functions from stb.h.
#include "getpath.h"


void init_launcher(void)
{
}

int get_thisfile(char *thisfile, const char *programname)
{
    char buf[PATH_MAX];
    char *p;

    /* Fill in thisfile. */
#ifdef __CYGWIN__
    if (strncasecmp(&programname[strlen(programname)-4], ".exe", 4)) {
        strcpy(thisfile, programname);
        strcat(thisfile, ".exe");
        PI_SetProgramName(thisfile);
    }
    else
#endif
    PI_SetProgramName(programname);

    strcpy(buf, PI_GetProgramFullPath());

    /* Make homepath absolute.
     * 'thisfile' starts ./ which breaks some modules when changing the CWD.
     */
    p = realpath(buf, thisfile);
    if(p == NULL) {
        FATALERROR("Error in making thisfile absolute.\n");
        return -1;
    }

    VS("thisfile is %s\n", thisfile);
    
    return 0;
}

void get_homepath(char *homepath, const char *thisfile)
{
    char buf[PATH_MAX];
    char *p;

    /* Fill in here (directory of thisfile). */
    strcpy(buf, PI_GetPrefix());

    /* Make homepath absolute.
     * 'homepath' contains ./ which breaks some modules when changing the CWD.
     * Relative LD_LIBRARY_PATH is a security problem.
     */
    p = realpath(buf, homepath);
    if(p == NULL) {
        FATALERROR("Error in making homepath absolute.\n");
        /* Fallback to relative path. */
        strcpy(homepath, buf);
    }

    /* Path must end with slash. / */
    strcat(homepath, "/");

    VS("homepath is %s\n", homepath);
}

void get_archivefile(char *archivefile, const char *thisfile)
{
    strcpy(archivefile, thisfile);
    strcat(archivefile, ".pkg");
}

static int set_dynamic_library_path(const char* path)
{
    int rc = 0;

#ifdef AIX
    /* LIBPATH is used to look up dynamic libraries on AIX. */
    setenv("LIBPATH", path, 1);
    VS("%s\n", path);
#else
    /* LD_LIBRARY_PATH is used on other *nix platforms (except Darwin). */
    rc = setenv("LD_LIBRARY_PATH", path, 1);
    VS("%s\n", path);
#endif /* AIX */

    return rc;
}

int set_environment(const ARCHIVE_STATUS *status)
{
    int rc = 0;

#ifdef __APPLE__
    /* On Mac OS X we do not use environment variables DYLD_LIBRARY_PATH
     * or others to tell OS where to look for dynamic libraries.
     * There were some issues with this approach. In some cases some
     * system libraries were trying to load incompatible libraries from
     * the dist directory. For instance this was experienced with macprots
     * and PyQt4 applications.
     *
     * To tell the OS where to look for dynamic libraries we modify
     * .so/.dylib files to use relative paths to other dependend
     * libraries starting with @executable_path.
     *
     * For more information see:
     * http://blogs.oracle.com/dipol/entry/dynamic_libraries_rpath_and_mac
     * http://developer.apple.com/library/mac/#documentation/DeveloperTools/  \
     *     Conceptual/DynamicLibraries/100-Articles/DynamicLibraryUsageGuidelines.html
     */
    /* For environment variable details see 'man dyld'. */
	unsetenv("DYLD_FRAMEWORK_PATH");
	unsetenv("DYLD_FALLBACK_FRAMEWORK_PATH");
	unsetenv("DYLD_VERSIONED_FRAMEWORK_PATH");
	unsetenv("DYLD_LIBRARY_PATH");
	unsetenv("DYLD_FALLBACK_LIBRARY_PATH");
	unsetenv("DYLD_VERSIONED_LIBRARY_PATH");
	unsetenv("DYLD_ROOT_PATH");

#else
    /* Set library path to temppath. This is only for onefile mode.*/
    if (status->temppath[0] != '\0') {
        rc = set_dynamic_library_path(status->temppath);
    }
    /* Set library path to homepath. This is for default onedir mode.*/
    else {
        rc = set_dynamic_library_path(status->homepath);
    }
#endif

    return rc;
}

/* Remember child process id. It allows sending a signal to child process.
 * Frozen application always runs in a child process. Parent process is used
 * to setup environment for child process and clean the environment when
 * child exited.
 */
pid_t child_pid = 0;

void signal_handler(int signal)
{
    kill(child_pid, signal);
}


/* Start frozen application in a subprocess. The frozen application runs
 * in a subprocess.
 */
int spawn(const char *thisfile, char *const argv[])
{
    pid_t pid = 0;
    int rc = 0;

    pid = fork();

    /* Child code. */
    if (pid == 0)
        /* Replace process by starting a new application. */
        execvp(thisfile, argv);
    /* Parent code. */
    else
    {
        child_pid = pid;

        /* Redirect termination signals received by parent to child process. */
        signal(SIGINT, &signal_handler);
        signal(SIGKILL, &signal_handler);
        signal(SIGTERM, &signal_handler);
    }

    wait(&rc);

    /* Parent code. */
    if(child_pid != 0 )
    {
        /* When child process exited, reset signal handlers to default values. */
        signal(SIGINT, SIG_DFL);
        signal(SIGKILL, SIG_DFL);
        signal(SIGTERM, SIG_DFL);
    }
    if (WIFEXITED(rc))
        return WEXITSTATUS(rc);
    /* Process ended abnormally */
    if (WIFSIGNALED(rc))
        /* Mimick the signal the child received */
        raise(WTERMSIG(rc));
    return 1;
}
