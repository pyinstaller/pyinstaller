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

// TODO: use safe string functions
#define _CRT_SECURE_NO_WARNINGS 1

#ifdef _WIN32
    #include <windows.h>  // GetModuleFileNameW
    #include <wchar.h>
#elif __APPLE__
    #include <libgen.h>  // basename(), dirname()
    #include <mach-o/dyld.h>  // _NSGetExecutablePath()
#else
    #include <libgen.h>  // basename()
    #include <limits.h>  // PATH_MAX
    #include <unistd.h>  // unlink
#endif

#include <stdio.h>  // FILE, fopen
#include <stdlib.h>  // _fullpath, realpath
#include <string.h>


/* PyInstaller headers. */
#include "pyi_global.h"  // PATH_MAX
#include "pyi_win32_utils.h"
#include "pyi_python27_compat.h"  // is_py2

/*
 * Giving a fullpath, it will copy to the buffer a string
 * which contains the path without last component.
 */
void pyi_path_dirname(char *result, const char *path)
{
// FIXME: This should be somthink like HAVE_DIRNAME
#ifdef _WIN32
    size_t len = 0;
    char *match = NULL;

    /* Copy path to result and then just write '\0' to the place with path separator. */
    strncpy(result, path, strlen(path)+1);
    /* Remove separator from the end. */
    len = strlen(result);
    if (result[len] == PYI_SEP) {
        result[len] = PYI_NULLCHAR;
    }
    /* Remove the rest of the string. */
    match = strrchr(result, PYI_SEP);
    if (match != NULL) {
        *match = PYI_NULLCHAR;
    } else {
      // No dir separator found, so no dir-part, so use current dir
      *result = PYI_CURDIR;
      result[1] = PYI_NULLCHAR;
    }
#else
    // Use dirname() for other platforms.
    char *dirpart = NULL;
    char tmp[PATH_MAX];
    // Copy path to 'tmp' because dirname() modifies the original string!
    strcpy(tmp, path);

    dirpart = (char *) dirname((char *) tmp);  // _XOPEN_SOURCE - no 'const'.
    strcpy(result, dirpart);
#endif
}


/*
 * Returns the last component of the path in filename. Return result
 * in new buffer.
 */
void pyi_path_basename(char *result, const char *path)
{
// FIXME: This should be somthink like HAVE_BASENAME
#ifdef _WIN32
  /* Search for the last directory separator in PATH.  */
  char *basename = strrchr (path, '\\');
  if (!basename) basename = strrchr (path, '/');
  
  /* If found, return the address of the following character,
     or the start of the parameter passed in.  */
  strcpy(result, basename ? ++basename : (char*)path);
#else
    char *base = NULL;
    base = (char *) basename((char *) path);  // _XOPEN_SOURCE - no 'const'.
    strcpy(result, base);
#endif
}


/*
 * Join two path components.
 * Joined path is returned without slash at the end.
 */
// FIXME: Need to test for absolut path2 -- or mark this function as
//        only for an relative path2
void pyi_path_join(char *result, const char *path1, const char *path2)
{ 
    size_t len = 0;
    memset(result, 0, PATH_MAX);
    /* Copy path1 to result null string '\0'. */
    strncpy(result, path1, strlen(path1));
    /* Append trailing slash if missing. */
    len = strlen(result);
    if (result[len-1] != PYI_SEP) {
        result[len] = PYI_SEP;
        result[len+1] = PYI_NULLCHAR;
    }
    /* Remove trailing slash from path2 if present. */
    len = strlen(path2);
    if (path2[len-1] == PYI_SEP) {
        /* Append path2 without slash. */
        strncat(result, path2, len-2);
    }
    else {
        /* path2 does not end with slash. */
        strcat(result, path2);
    }
}


/* Normalize a pathname. Return result in new buffer. */
// TODO implement this function
void pyi_path_normalize(char *result, const char *path)
{
}


/*
 * Return full path to a file. Wraps platform specific function.
 */
int pyi_path_fullpath(char *abs, size_t abs_size, const char *rel)
{
   #ifdef _WIN32
       // TODO use _wfullpath - wchar_t function.
       return _fullpath(abs, rel, abs_size) != NULL;
   #else
       return realpath(rel, abs) != NULL;
   #endif
}


/*
 * Return full path to the current executable.
 * Executable is the .exe created by pyinstaller: path/myappname.exe
 *
 * execfile - buffer where to put path to executable.
 * appname - usually the item argv[0].
 */
int pyi_path_executable(char *execfile, const char *appname)
{
    char buffer[PATH_MAX];
#ifdef _WIN32

	if (!is_py2) {
        /* Use utf8 form of argv[0] as is */
        strncpy(buffer, appname, PATH_MAX);
    } else {
        /* Convert argv[0] to ShortFileName, preserving basename of exe */
        pyi_win32_utf8_to_mbs_sfn_keep_basename(buffer, appname);
    }

#elif __APPLE__
    uint32_t length = sizeof(buffer);

    /* Mac OS X has special function to obtain path to executable. */
    if (_NSGetExecutablePath(buffer, &length) != 0) {
        FATALERROR("System error - unable to load!");
		return -1;
    }

#else
    // On Linux absolute path is from symlink /prox/PID/exe
    strncpy(buffer, appname, PATH_MAX);
    // TODO: This should be made an absolute path. A for now this is
    // done by calling pyi_path_fullpath below.
#endif
    /*
     * Ensure path to executable is absolute.
     * 'execfile' starting with ./ might break some modules when changing
     * the CWD.From 'execfile' is constructed 'homepath' and homepath is used
     * for LD_LIBRARY_PATH variavle. Relative LD_LIBRARY_PATH is a security
     * problem.
     */
    // FIXME: Use pyi_path_normalize (which keeps symlinks) instead of
    //        pyi_path_fullpath (which removes symlinks) to solve
    //        issue #1208.
    if(pyi_path_fullpath(execfile, PATH_MAX, buffer) == false) {
        VS("LOADER: executable is %s\n", execfile);
        return -1;
    }
 
    VS("LOADER: executable is %s\n", execfile);

	return 0;
}


/*
 * Return absolute path to homepath. It is the directory containing executable.
 */
void pyi_path_homepath(char *homepath, const char *thisfile)
{
    /* Fill in here (directory of thisfile). */
    pyi_path_dirname(homepath, thisfile);
    VS("LOADER: homepath is %s\n", homepath);
}


/*
 * Return full path to an external PYZ-archive.
 * The name is based on the excutable's name: path/myappname.pkg
 *
 * archivefile - buffer where to put path the .pkg.
 * thisfile    - usually the executable's filename.
 */
void pyi_path_archivefile(char *archivefile, const char *thisfile)
{
	strcpy(archivefile, thisfile);
#ifdef _WIN32
	strcpy(archivefile + strlen(archivefile) - 3, "pkg");
#else
    strcat(archivefile, ".pkg");
#endif
}


/*
 * Multiplatform wrapper around function fopen().
 */
#ifdef _WIN32
FILE* pyi_path_fopen(const char* filename, const char* mode) {
    wchar_t wfilename[MAX_PATH];
    wchar_t wmode[10];
    pyi_win32_utils_from_utf8(wfilename, filename, MAX_PATH);
    pyi_win32_utils_from_utf8(wmode, mode, 10);
    return _wfopen(wfilename, wmode);
}
#else
   #define pyi_path_fopen(x,y)    fopen(x,y)
#endif
