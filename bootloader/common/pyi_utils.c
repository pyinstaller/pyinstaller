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
 * Portable wrapper for some utility functions like getenv/setenv,
 * file path manipulation and other shared data types or functions.
 */


#ifdef WIN32
    #include <windows.h>
    #include <direct.h>  // _mkdir, _rmdir
    #include <io.h>  // _finddata_t
    #include <process.h>  // getpid
    #include <signal.h>  // signal
#else
    #include <dirent.h>
    #include <dlfcn.h>
    #include <limits.h>  // PATH_MAX
    #include <signal.h>  // kill,
    #include <sys/wait.h>
    #include <unistd.h>  // rmdir, unlink
#endif
#include <stddef.h>  // ptrdiff_t
#include <stdio.h>  // FILE
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>  // struct stat

/*
 * Function 'mkdtemp' (make temporary directory) is missing on some *nix platforms: 
 * - On Solaris function 'mkdtemp' is missing.
 * - On AIX 5.2 function 'mkdtemp' is missing. It is there in version 6.1 but we don't know
 *   the runtime platform at compile time, so we always include our own implementation on AIX.
 */
#if defined(SUNOS) || defined(AIX)
    #include "mkdtemp.h"
#endif


/* PyInstaller headers. */
#include "stb.h"
#include "pyi_global.h"
#include "pyi_archive.h"
#include "pyi_utils.h"
// TODO Eliminate getpath.c/.h and replace it with functions from stb.h.
#include "getpath.h"


/* Return string copy of environment variable. */
// TODO unicode support
char *pyi_getenv(const char *variable)
{
    char *env = NULL;

#ifdef WIN32
    char  buf1[PATH_MAX], buf2[PATH_MAX];
    DWORD rc;

    rc = GetEnvironmentVariableA(variable, buf1, sizeof(buf1));
    if(rc > 0) {
        env = buf1;
        /* Expand environment variables like %VAR% in value. */
        rc = ExpandEnvironmentStringsA(env, buf2, sizeof(buf2));
        if(rc > 0) {
            env = buf1;
        }
    }
#else
    /* Standard POSIX function. */
    env = getenv(variable);
#endif
    /* Return copy of string. */
    return (env && env[0]) ? strdup(env) : NULL;
}


/* Set environment variable. */
// TODO unicode support
int pyi_setenv(const char *variable, const char *value)
{
    int rc;
#ifdef WIN32
    rc = SetEnvironmentVariableA(variable, value);
#else
    rc = setenv(variable, value, true);
#endif
    return rc;
}


/* Unset environment variable. */
// TODO unicode support
int pyi_unsetenv(const char *variable)
{
    int rc;
#ifdef WIN32
    rc = SetEnvironmentVariableA(variable, NULL);
#else
    rc = unsetenv(variable);
#endif
    return rc;
}


#ifdef WIN32

// TODO rename fuction and revisit
int pyi_get_temp_path(char *buff)
{
    int i;
    char *ret;
    char prefix[16];

    GetTempPath(PATH_MAX, buff);
    sprintf(prefix, "_MEI%d", getpid());

    // Windows does not have a race-free function to create a temporary
    // directory. Thus, we rely on _tempnam, and simply try several times
    // to avoid stupid race conditions.
    for (i=0;i<5;i++) {
        // TODO use race-free fuction - if any exists?
        ret = _tempnam(buff, prefix);
        if (mkdir(ret) == 0) {
            strcpy(buff, ret);
            strcat(buff, PYI_SEPSTR);
            free(ret);
            return 1;
        }
        free(ret);
    }
    return 0;
}

#else

// TODO Is this really necessary to test for temp path? Why not just use mkdtemp()?
int pyi_test_temp_path(char *buff)
{
	strcat(buff, "/_MEIXXXXXX");
    if (mkdtemp(buff))
    {
        strcat(buff, PYI_SEPSTR);
        return 1;
    }
    return 0;
}

// TODO merge this function with windows version.
static int pyi_get_temp_path(char *buff)
{
    // TODO Do we need to check on unix for common variables paths to temp dirs?
	static const char *envname[] = {
		"TMPDIR", "TEMP", "TMP", 0
	};
	static const char *dirname[] = {
		"/tmp", "/var/tmp", "/usr/tmp", 0
	};
	int i;
	char *p;
	for ( i=0; envname[i]; i++ ) {
		p = pyi_getenv(envname[i]);
		if (p) {
			strcpy(buff, p);
			if (pyi_test_temp_path(buff))
				return 1;
		}
	}
	for ( i=0; dirname[i]; i++ ) {
		strcpy(buff, dirname[i]);
		if (pyi_test_temp_path(buff))
			return 1;
	}
    return 0;
}

#endif


/*
 * Creates a temporany directory if it doesn't exists
 * and properly sets the ARCHIVE_STATUS members.
 */
int pyi_create_temp_path(ARCHIVE_STATUS *status)
{
#ifdef WIN32
	char *p;
#endif
  
	if (status->has_temp_directory != true) {
		if (!pyi_get_temp_path(status->temppath))
		{
            FATALERROR("INTERNAL ERROR: cannot create temporary directory!\n");
            return -1;
		}
        /* Set flag that temp directory is created and available. */
        status->has_temp_directory = true;
#ifdef WIN32
		strcpy(status->temppathraw, status->temppath);
		for ( p=status->temppath; *p; p++ )
			if (*p == '\\')
				*p = '/';
#endif
	}
    return 0;
}


// TODO merge unix/win versions of remove_one() and pyi_remove_temp_path()
#ifdef WIN32
static void remove_one(char *fnm, int pos, struct _finddata_t finfo)
{
	if ( strcmp(finfo.name, ".")==0  || strcmp(finfo.name, "..") == 0 )
		return;
	fnm[pos] = PYI_NULLCHAR;
	strcat(fnm, finfo.name);
	if ( finfo.attrib & _A_SUBDIR )
        /* Use recursion to remove subdirectories. */
		pyi_remove_temp_path(fnm);
	else if (remove(fnm)) {
        /* HACK: Possible concurrency issue... spin a little while */
        Sleep(100);
        remove(fnm);
    }
}

//TODO Find easier and more portable implementation of removing directory recursively.
//     e.g.
void pyi_remove_temp_path(const char *dir)
{
	char fnm[PATH_MAX+1];
	struct _finddata_t finfo;
	long h;
	int dirnmlen;
	strcpy(fnm, dir);
	dirnmlen = strlen(fnm);
	if ( fnm[dirnmlen-1] != '/' && fnm[dirnmlen-1] != '\\' ) {
		strcat(fnm, "\\");
		dirnmlen++;
	}
	strcat(fnm, "*");
	h = _findfirst(fnm, &finfo);
	if (h != -1) {
		remove_one(fnm, dirnmlen, finfo);
		while ( _findnext(h, &finfo) == 0 )
			remove_one(fnm, dirnmlen, finfo);
		_findclose(h);
	}
	rmdir(dir);
}
#else
static void remove_one(char *pnm, int pos, const char *fnm)
{
	struct stat sbuf;
	if ( strcmp(fnm, ".")==0  || strcmp(fnm, "..") == 0 )
		return;
	pnm[pos] = PYI_NULLCHAR;
	strcat(pnm, fnm);
	if ( stat(pnm, &sbuf) == 0 ) {
		if ( S_ISDIR(sbuf.st_mode) )
            /* Use recursion to remove subdirectories. */
			pyi_remove_temp_path(pnm);
		else
			unlink(pnm);
	}
}

void pyi_remove_temp_path(const char *dir)
{
	char fnm[PATH_MAX+1];
	DIR *ds;
	struct dirent *finfo;
	int dirnmlen;

	strcpy(fnm, dir);
	dirnmlen = strlen(fnm);
	if ( fnm[dirnmlen-1] != PYI_SEP) {
		strcat(fnm, PYI_SEPSTR);
		dirnmlen++;
	}
	ds = opendir(dir);
	finfo = readdir(ds);
	while (finfo) {
		remove_one(fnm, dirnmlen, finfo->d_name);
		finfo = readdir(ds);
	}
	closedir(ds);
	rmdir(dir);
}
#endif


// TODO is this function still used? Could it be removed?
/*
 * If binaries were extracted, this should be called
 * to remove them
 */
void cleanUp(ARCHIVE_STATUS *status)
{
	if (status->temppath[0])
		pyi_remove_temp_path(status->temppath);
}



/*
 * helper for extract2fs
 * which may try multiple places
 */
//TODO find better name for function.
FILE *pyi_open_target(const char *path, const char* name_)
{
	struct stat sbuf;
	char fnm[PATH_MAX+1];
	char name[PATH_MAX+1];
	char *dir;

	strcpy(fnm, path);
	strcpy(name, name_);
	fnm[strlen(fnm)-1] = PYI_NULLCHAR;

	dir = strtok(name, PYI_SEPSTR);
	while (dir != NULL)
	{
		strcat(fnm, PYI_SEPSTR);
		strcat(fnm, dir);
		dir = strtok(NULL, PYI_SEPSTR);
		if (!dir)
			break;
		if (stat(fnm, &sbuf) < 0)
    {
#ifdef WIN32
			mkdir(fnm);
#else
			mkdir(fnm, 0700);
#endif
    }
	}

	if (stat(fnm, &sbuf) == 0) {
		OTHERERROR("WARNING: file already exists but should not: %s\n", fnm);
    }
    /*
     * stb__fopen() wraps different fopen names. On Windows it uses
     * wide-character version of fopen.
     */
	return stb__fopen(fnm, "wb");
}

/* Copy the file src to dst 4KB per time */
int pyi_copy_file(const char *src, const char *dst, const char *filename)
{
    FILE *in = stb_fopen(src, "rb");
    FILE *out = pyi_open_target(dst, filename);
    char buf[4096];
    int error = 0;

    if (in == NULL || out == NULL)
        return -1;

    while (!feof(in)) {
        if (fread(buf, 4096, 1, in) == -1) {
            if (ferror(in)) {
                clearerr(in);
                error = -1;
                break;
            }
        } else {
            fwrite(buf, 4096, 1, out);
            if (ferror(out)) {
                clearerr(out);
                error = -1;
                break;
            }
        }
    }
#ifndef WIN32
    fchmod(fileno(out), S_IRUSR | S_IWUSR | S_IXUSR);
#endif
    fclose(in);
    fclose(out);

    return error;
}


/*
 * Giving a fullpath, returns a newly allocated string
 * which contains the directory name.
 * The returned string must be freed after use.
 */
// TODO use for unix function dirname()
char *pyi_path_dirname(const char *fullpath)
{
    char *match = strrchr(fullpath, PYI_SEP);
    char *pathname = (char *) calloc(PATH_MAX, sizeof(char));
    VS("Calculating dirname from fullpath\n");
    if (match != NULL)
        strncpy(pathname, fullpath, match - fullpath + 1);
    else
        strcpy(pathname, fullpath);

    VS("Pathname: %s\n", pathname);
    return pathname;
}

/*
 * Returns the last component of the path in filename. Return result
 * in new buffer.
 */
// TODO use for unix function basename()
// TODO For now it is win32 implementation only!
char *pyi_path_basename(const char *path)
{
  /* Search for the last directory separator in PATH.  */
  char *basename = strrchr (path, '\\');
  if (!basename) basename = strrchr (path, '/');
  
  /* If found, return the address of the following character,
     or the start of the parameter passed in.  */
  return basename ? ++basename : (char*)path;
}

/*
 * Join two path components. Return result in new buffer.
 * Joined path is returned without slash at the end.
 */
char *pyi_path_join(const char *path1, const char *path2)
{ 
    char *joined = strdup(path1);
    size_t len = 0;
    /* Append trailing slash if missing. */
    len = strlen(joined);
    if (joined[len-1] != PYI_SEP) {
        joined[len] = PYI_SEP;
        joined[len+1] = PYI_NULLCHAR;
    }
    /* Append second component to path1 without trailing slash. */
    strcat(joined, path2);
    /* Remove trailing slash if present. */
    len = strlen(path2);
    if (path2[len-1] == PYI_SEP) {
        /* Append path2 without slash. */
        strncat(joined, path2, len-2);
    }
    else {
        /* path2 does not end with slash. */
        strcat(joined, path2);
    }
    return joined;
}

/* Normalize a pathname. Return result in new buffer. */
// TODO implement this function
char *pyi_path_normalize(const char *path)
{
    return NULL;
}


// TODO use dlclose() when exiting.
/* Load the shared dynamic library (DLL) */
dylib_t pyi_dlopen(const char *dllpath)
{

#ifdef WIN32
    //char buff[PATH_MAX] = NULL;
#else
    int dlopenMode = RTLD_NOW | RTLD_GLOBAL;
#endif

#ifdef AIX
    /* Append the RTLD_MEMBER to the open mode for 'dlopen()'
     * in order to load shared object member from library.
     */
    dlopenMode |= RTLD_MEMBER;
#endif

#ifdef WIN32
    /* Use unicode version of function to load  dll file. */
	//return LoadLibraryExW(stb_to_utf8(buff, dllpath, sizeof(buff)), NULL,
            //LOAD_WITH_ALTERED_SEARCH_PATH);
	return LoadLibraryEx(dllpath, NULL, LOAD_WITH_ALTERED_SEARCH_PATH);
#else
	return dlopen(dllpath, dlopenMode);
#endif

}


////////////////////////////////////////////////////////////////////
// TODO better merging of the following platform specific functions.
////////////////////////////////////////////////////////////////////


#ifdef WIN32


int pyi_utils_set_environment(const ARCHIVE_STATUS *status)
{
	return 0;
}

int pyi_utils_create_child(const char *thisfile, char *const argv[])
{
	SECURITY_ATTRIBUTES sa;
	STARTUPINFOW si;
	PROCESS_INFORMATION pi;
	int rc = 0;
    stb__wchar buffer[PATH_MAX];

    /* Convert file name to wchar_t from utf8. */
    stb_from_utf8(buffer, thisfile, PATH_MAX);

	// the parent process should ignore all signals it can
	signal(SIGABRT, SIG_IGN);
	signal(SIGINT, SIG_IGN);
	signal(SIGTERM, SIG_IGN);
	signal(SIGBREAK, SIG_IGN);

	VS("Setting up to run child\n");
	sa.nLength = sizeof(sa);
	sa.lpSecurityDescriptor = NULL;
	sa.bInheritHandle = TRUE;
	GetStartupInfoW(&si);
	si.lpReserved = NULL;
	si.lpDesktop = NULL;
	si.lpTitle = NULL;
	si.dwFlags = STARTF_USESTDHANDLES | STARTF_USESHOWWINDOW;
	si.wShowWindow = SW_NORMAL;
	si.hStdInput = (void*)_get_osfhandle(fileno(stdin));
	si.hStdOutput = (void*)_get_osfhandle(fileno(stdout));
	si.hStdError = (void*)_get_osfhandle(fileno(stderr));

	VS("Creating child process\n");
	if (CreateProcessW( 
			buffer,  // Pointer to name of executable module.
			GetCommandLineW(),  // pointer to command line string 
			&sa,  // pointer to process security attributes 
			NULL,  // pointer to thread security attributes 
			TRUE,  // handle inheritance flag 
			0,  // creation flags 
			NULL,  // pointer to new environment block 
			NULL,  // pointer to current directory name 
			&si,  // pointer to STARTUPINFO 
			&pi  // pointer to PROCESS_INFORMATION 
			)) {
		VS("Waiting for child process to finish...\n");
		WaitForSingleObject(pi.hProcess, INFINITE);
		GetExitCodeProcess(pi.hProcess, (unsigned long *)&rc);
	} else {
		FATALERROR("Error creating child process!\n");
		rc = -1;
	}
	return rc;
}


#else


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

int pyi_utils_set_environment(const ARCHIVE_STATUS *status)
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

static void _signal_handler(int signal)
{
    kill(child_pid, signal);
}


/* Start frozen application in a subprocess. The frozen application runs
 * in a subprocess.
 */
int pyi_utils_create_child(const char *thisfile, char *const argv[])
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
        signal(SIGINT, &_signal_handler);
        signal(SIGKILL, &_signal_handler);
        signal(SIGTERM, &_signal_handler);
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


#endif  /* WIN32 */
