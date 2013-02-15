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
    stb__wchar buffer[PATH_MAX];
	if (!GetModuleFileNameW(NULL, buffer, PATH_MAX)) {
		FATALERROR("System error - unable to load!");
		return -1;
	}
    /* Convert wchar_t to utf8 just use char as usual. */
    stb_to_utf8(execfile, buffer, PATH_MAX);

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
    VS("LOADER: executable is %s\n", execfile);
 
	return 0;
}


/*
 * Return absolute path to homepath. It is the directory containing executable.
 */
void pyi_path_homepath(char *homepath, const char *thisfile)
{
    // TODO merge platform specific as much as it is possible.
#ifdef WIN32
	char *p = NULL;
	
	strcpy(homepath, thisfile);
	for (p = homepath + strlen(homepath); *p != PYI_SEP && p >= homepath + 2; --p);
	*++p = PYI_NULLCHAR;
#else
    char buf[PATH_MAX];
    char *p;

    /* Fill in here (directory of thisfile). */
    strcpy(buf, PI_GetPrefix());

    // TODO move the code to create absolute path to 'pyi_path_executable'.
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

    VS("LOADER: homepath is %s\n", homepath);
#endif
}


// TODO What is the purpose of this function and the variable 'archivefile'?
void pyi_path_archivefile(char *archivefile, const char *thisfile)
{
	strcpy(archivefile, thisfile);
#ifdef WIN32
	strcpy(archivefile + strlen(archivefile) - 3, "pkg");
#else
    strcat(archivefile, ".pkg");
#endif
}
