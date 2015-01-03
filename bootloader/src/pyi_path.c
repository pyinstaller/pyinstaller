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


#ifdef _WIN32
    #include <windows.h>  // GetModuleFileNameW
    #include <wchar.h>
#elif __APPLE__
    #include <libgen.h>  // basename()
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


/*
 * Giving a fullpath, it will copy to the buffer a string
 * which contains the path without last component.
 */
// TODO use for unix function dirname()
void pyi_path_dirname(char *result, const char *path)
{
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
    }
}


/*
 * Returns the last component of the path in filename. Return result
 * in new buffer.
 */
void pyi_path_basename(char *result, const char *path)
{
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
    strcpy(result, path);
#endif
}


/*
 * Join two path components.
 * Joined path is returned without slash at the end.
 */
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
    char dos83_buffer[PATH_MAX];
    wchar_t wchar_buffer[PATH_MAX];
    wchar_t wchar_dos83_buffer[PATH_MAX];
    char basename[PATH_MAX];
    char dirname[PATH_MAX];

    /* Windows has special function to obtain path to executable. */
	if (!GetModuleFileNameW(NULL, wchar_buffer, PATH_MAX)) {
		FATALERROR("System error - unable to load!");
		return -1;
	}
    /* Convert wchar_t to utf8 - just use type char as usual. */
    pyi_win32_utils_to_utf8(buffer, wchar_buffer, PATH_MAX);

    // TODO do not use this workaround for Python 3.
    /*
     * Use 8.3 filename (dos 8.3 or short filename)
     * to overcome the Python and PyInstaller limitation
     * to run with foreign characters in directory names.
     *
     * If 8.3 filename does not exist, original vaule is just copied
     * to the supplied buffer. 8.3 filename might not be available
     * for some networking file systems.
     *
     * This is workaround for <http://www.pyinstaller.org/ticket/298>.
     */
    GetShortPathNameW(wchar_buffer, wchar_dos83_buffer, PATH_MAX);
    /* Convert wchar_t to utf8 just use char as usual. */
    pyi_win32_utils_to_utf8(dos83_buffer, wchar_dos83_buffer, PATH_MAX);

    /*
     * Construct proper execfile -  83_DIRNAME + full_basename.
     * GetShortPathName() makes also the basename (appname.exe) shorter.
     *
     * However, bootloader code depends on unmodified basename.
     * Using basename from original path should fix this.
     * It is supposed that basename does not contain any foreign characters.
     *
     * Reuse 'buffer' variable.
     */
    pyi_path_basename(basename, buffer);
    pyi_path_dirname(dirname, dos83_buffer);
    pyi_path_join(buffer, dirname, basename);

#elif __APPLE__
    uint32_t length = sizeof(buffer);

    /* Mac OS X has special function to obtain path to executable. */
    if (_NSGetExecutablePath(buffer, &length) != 0) {
        FATALERROR("System error - unable to load!");
		return -1;
    }

#else
    int  numchars;
    // On Linux absolute path is from symlink /prox/PID/exe
    char proc_path[PATH_MAX+1];
    sprintf(proc_path, "/proc/%d/exe", getpid());
    // Read the real path from symlink.
    numchars = readlink(proc_path, buffer, PATH_MAX);
    // readlink() return number of read characters without ending '\0'.
    if (numchars > 0) {
        buffer[numchars] = '\0';
    }
    else {
        FATALERROR("System error - unable to load!");
		return -1;
	}
#endif
    /*
     * Ensure path to executable is absolute.
     * 'execfile' starting with ./ might break some modules when changing
     * the CWD.From 'execfile' is constructed 'homepath' and homepath is used
     * for LD_LIBRARY_PATH variavle. Relative LD_LIBRARY_PATH is a security
     * problem.
     */
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


// TODO What is the purpose of this function and the variable 'archivefile'?
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
