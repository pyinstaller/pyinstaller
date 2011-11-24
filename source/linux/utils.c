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
#include <stdlib.h>
#include <limits.h>
#include <sys/wait.h>
#include <signal.h>

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

static int prepend2enviroment(const char *name, const char *value)
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

static int prependToDynamicLibraryPath(const char* path)
{
    int rc = 0;

#ifdef AIX
    /* LIBPATH is used to look up dynamic libraries on AIX. */
    rc = prepend2enviroment("LIBPATH", path);
#else
    /* LD_LIBRARY_PATH is used on other *nix platforms (except Darwin). */
    rc = prepend2enviroment("LD_LIBRARY_PATH", path);
#endif /* AIX */

    return rc;
}

int set_environment(const ARCHIVE_STATUS *status)
{
    int rc = 0;
    char buf[PATH_MAX+2];
    char *p;

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
    /* add temppath to library path */
    if (status->temppath[0] != 0) {
        rc = prependToDynamicLibraryPath(status->temppath);
    }
    /* make homepath absolute
     * homepath contains ./ which breaks some modules when changing the CWD.
     * Relative LD_LIBRARY_PATH is also a security problem.
     */
    p = realpath(status->homepath, buf);
    if(p == NULL) {
        FATALERROR("Error in making homepath absolute.\n");
        return -1;
    }

    /* path must end with slash / */
    strcat(buf, "/");
    rc = prependToDynamicLibraryPath(buf);
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

    return WEXITSTATUS(rc);
}
