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
 * Path manipulation utilities.
 */


#ifdef WIN32
    #include <windows.h>  // GetModuleFileNameW
    #include <wchar.h>
#elif __APPLE__
    #include <mach-o/dyld.h>  // _NSGetExecutablePath()
#else
    #include <limits.h>  // PATH_MAX
    // TODO Eliminate getpath.c/.h and replace it with functions from stb.h.
    #include "getpath.h"
#endif


/* PyInstaller headers. */
#include "stb.h"
#include "pyi_global.h"  // PATH_MAX
//#include "pyi_archive.h"
//#include "pyi_utils.h"


/*
 * Return full path to the current executable.
 * Executable is the .exe created by pyinstaller: path/myappname.exe
 *
 * execfile - buffer where to put path to executable.
 * appname - usually the item argv[0].
 */
int pyi_path_executable(char *execfile, const char *appname)
{
    /* Windows has special function to obtain path to executable. */
#ifdef WIN32
    stb__wchar wcharfile[PATH_MAX];
	if (!GetModuleFileNameW(NULL, (* LPWSTR) wcharfile, PATH_MAX)) {
		FATALERROR("System error - unable to load!");
		return -1;
	}
    /* Convert wchar_t to utf8 just use char as usual. */
    stb_to_utf8(execfile, wcharfile, PATH_MAX);

    /* Windows has special function to obtain path to executable. */
// TODO implement 
//#elif __APPLE__    _NSGetExecutablePath()
#else
    char buf[PATH_MAX];
    char *p;

    /* Fill in thisfile. */
    #ifdef __CYGWIN__
    if (strncasecmp(&appname[strlen(appname)-4], ".exe", 4)) {
        strcpy(execfile, appname);
        strcat(execfile, ".exe");
        PI_SetProgramName(execfile);
    }
    else
    #endif /* __CYGWIN__ */
    PI_SetProgramName(appname);

    strcpy(buf, PI_GetProgramFullPath());

    /* Make homepath absolute.
     * 'thisfile' starts ./ which breaks some modules when changing the CWD.
     */
    p = realpath(buf, execfile);
    if(p == NULL) {
        FATALERROR("Error in making thisfile absolute.\n");
        return -1;
    }

#endif
    VS("executable is %s\n", execfile);
 
	return 0;
}


