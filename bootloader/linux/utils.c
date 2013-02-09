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
 * Some Linux/Unix utility functions.
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
    if (status->temppath[0] != PYI_NULLCHAR) {
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
