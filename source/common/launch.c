/*
 * Launch a python module from an archive.
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
#include <stdio.h>
#include "pyi_unicode.h"
#ifdef WIN32
 #include <windows.h>
 #include <direct.h>
 #include <process.h>
 #include <io.h>
 #define unsetenv(x) _tputenv(x _T("="))
#else
 #include <unistd.h>
 #include <fcntl.h>
 #include <dlfcn.h>
 #include <dirent.h>
 #include <stdarg.h>
#endif
#include <sys/types.h>
#include <sys/stat.h>
#include "launch.h"
#include <string.h>
#include "zlib.h"



/*
 * Python Entry point declarations (see macros in launch.h).
 */
DECLVAR(Py_FrozenFlag);
DECLVAR(Py_NoSiteFlag);
DECLVAR(Py_OptimizeFlag);
DECLVAR(Py_VerboseFlag);
DECLPROC(Py_Initialize);
DECLPROC(Py_Finalize);
DECLPROC(Py_IncRef);
DECLPROC(Py_DecRef);
DECLPROC(PyImport_ExecCodeModule);
DECLPROC(PyRun_SimpleString);
DECLPROC(PySys_SetArgv);
DECLPROC(Py_SetProgramName);
DECLPROC(PyImport_ImportModule);
DECLPROC(PyImport_AddModule);
DECLPROC(PyObject_SetAttrString);
DECLPROC(PyList_New);
DECLPROC(PyList_Append);
DECLPROC(Py_BuildValue);
DECLPROC(PyString_FromStringAndSize);
DECLPROC(PyFile_FromString);
DECLPROC(PyString_AsString);
DECLPROC(PyObject_CallFunction);
DECLPROC(PyModule_GetDict);
DECLPROC(PyDict_GetItemString);
DECLPROC(PyErr_Clear);
DECLPROC(PyErr_Occurred);
DECLPROC(PyErr_Print);
DECLPROC(PyObject_CallObject);
DECLPROC(PyObject_CallMethod);
DECLPROC(PySys_AddWarnOption);
DECLPROC(PyEval_InitThreads);
DECLPROC(PyEval_AcquireThread);
DECLPROC(PyEval_ReleaseThread);
DECLPROC(PyThreadState_Swap);
DECLPROC(Py_NewInterpreter);
DECLPROC(Py_EndInterpreter);
DECLPROC(PyInt_AsLong);
DECLPROC(PySys_SetObject);
DECLPROC(PyUnicodeUCS2_FromUnicode);  
DECLPROC(PyUnicodeUCS4_FromUnicode);  
DECLPROC(PyObject_GetAttr);
DECLPROC(PyString_FromString);


#ifdef WIN32
#define PATHSEPA ";"
#define SEPA '\\'
#else
#define PATHSEPA ":"
#define SEPA '/'
#endif
#define PATHSEP _T(PATHSEPA)
#define SEP _T(SEPA)

unsigned char *extract(ARCHIVE_STATUS *status, TOC *ptoc);

/*
 * The functions in this file defined in reverse order so that forward
 * declarations are not necessary.
 */


#if defined(WIN32) && defined(WINDOWED)
/* The code duplication in the functions below are because
 * standard macros with variable numer of arguments (variadic macros) are
 * supported by Microsoft only starting from Visual C++ 2005.
 */

#define MBTXTLEN 200

void mbfatalerror(const TCHAR *fmt, ...)
{
	TCHAR msg[MBTXTLEN];
	va_list args;

	va_start(args, fmt);
	_vsntprintf(msg, MBTXTLEN, fmt, args);
	msg[MBTXTLEN-1] = _T('\0');
	va_end(args);

	MessageBox(NULL, msg, _T("Fatal Error!"), MB_OK | MB_ICONEXCLAMATION);
}

void mbothererror(const TCHAR *fmt, ...)
{
	TCHAR msg[MBTXTLEN];
	va_list args;

	va_start(args, fmt);
	_vsntprintf(msg, MBTXTLEN, fmt, args);
	msg[MBTXTLEN-1] = _T('\0');
	va_end(args);

	MessageBox(NULL, msg, _T("Error!"), MB_OK | MB_ICONWARNING); 
}

void mbvs(const TCHAR *fmt, ...)
{
	TCHAR msg[MBTXTLEN];
	va_list args;

	va_start(args, fmt);
	_vsntprintf(msg, MBTXTLEN, fmt, args);
	msg[MBTXTLEN-1] = _T('\0');
	va_end(args);

	MessageBoxA(NULL, msg, _T("Tracing"), MB_OK);
}

#endif /* WIN32 and WINDOWED */


#ifdef WIN32

int getTempPath(TCHAR *buff)
{
    int i;
    TCHAR *ret;
    TCHAR prefix[16];

    GetTempPath(MAX_PATH, buff);
    _stprintf(prefix, _T("_MEI%d"), getpid());

    // Windows does not have a race-free function to create a temporary
    // directory. Thus, we rely on _tempnam, and simply try several times
    // to avoid stupid race conditions.
    for (i=0;i<5;i++) {
		ret = _ttempnam(buff, prefix); 
        if (_tmkdir(ret) == 0) {
            _tcscpy(buff, ret);
            _tcscat(buff, _T("\\"));
            free(ret);
            return 1;
        }
        free(ret);
    }
    return 0;
}

#else  // not windows.
// UNICODE note: here, we have more control over the directories we are choosing as temp directories.  So,
// there is no need (yet) to unicode this part.
int testTempPath(char *buff)
{
	_tcscat(buff, "/_MEIXXXXXX");
    if (mkdtemp(buff))
    {
        _tcscat(buff, "/");
        return 1;
    }
    return 0;
}

int getTempPath(char *buff)
{
	static const TCHAR *envname[] = {
		"TMPDIR", "TEMP", "TMP", 0
	};
	static const char *dirname[] = {
		"/tmp", "/var/tmp", "/usr/tmp", 0
	};
	int i;
	char *p;
	for ( i=0; envname[i]; i++ ) {
		p = getenv(envname[i]);
		if (p) {
			strcpy(buff, p);
			if (testTempPath(buff))
				return 1;
		}
	}
	for ( i=0; dirname[i]; i++ ) {
		strcpy(buff, dirname[i]);
		if (testTempPath(buff))
			return 1;
	}
    return 0;
}

#endif // end platforms other than windows.



static int checkFile(TCHAR *buf, const TCHAR *fmt, ...) 
{
	va_list args;
    struct stat tmp;

    va_start(args, fmt);
    _vsntprintf(buf, _MAX_PATH, fmt, args);
    va_end(args);

    return _tstat(buf, &tmp);
}


void BackslashToFrontslash(TCHAR *pth)
{
#ifndef WIN32
	return;
#else
	TCHAR *p;
#ifdef UNICODE
	TCHAR buffer[_MAX_PATH + 1];
	// super argh.  I'm sure that there is a better way of doing this, but I just can't think of a better
	// method at the moment.  Tokenize the string at the backslashes, and put it back together with frontslashes.
	_tcscpy(buffer,_T("\0"));
	p = _tcstok(pth,_T("\\"));
	while (p)
	{
		_tcscat(buffer,p);
		p = _tcstok(NULL,_T("\\"));
		_tcscat(buffer,_T("/"));
	}
	_tcscpy(pth,buffer);
#else
	for ( p = pth; *p; p++ )
		if (*p == '\\')
			*p = '/';
#endif
#endif
}

/*
 * Set up paths required by rest of this module
 * Sets f_archivename, f_homepath
 */
int setPaths(ARCHIVE_STATUS *status, TCHAR const * archivePath, TCHAR const * archiveName)
{
	/* Get the archive Path */
	_tcscpy(status->archivename, archivePath);
	_tcscat(status->archivename, archiveName);

	/* Set homepath to where the archive is */
	_tcscpy(status->homepath, archivePath);
#ifdef WIN32
	_tcscpy(status->homepathraw, archivePath);
	BackslashToFrontslash(status->homepath);

	VS(_T("HOMEPATH   : %s\n"),status->homepath);
	VS(_T("HOMEPATHRAW: %s\n"),status->homepathraw);
#endif

	return 0;
}

int checkCookie(ARCHIVE_STATUS *status, int filelen)
{
	if (fseek(status->fp, filelen-(int)sizeof(COOKIE), SEEK_SET))
		return -1;

	/* Read the Cookie, and check its MAGIC bytes */
	if (fread(&(status->cookie), sizeof(COOKIE), 1, status->fp) < 1)
	    return -1;
	if (strncmp(status->cookie.magic, MAGIC, strlen(MAGIC)))
		return -1;

  return 0;
}

int findDigitalSignature(ARCHIVE_STATUS * const status)
{
#ifdef WIN32
	/* There might be a digital signature attached. Let's see. */
	char buf[2];
	int offset = 0;
	fseek(status->fp, 0, SEEK_SET);
	fread(buf, 1, 2, status->fp);
	if (!(buf[0] == 'M' && buf[1] == 'Z'))
		return -1;
	/* Skip MSDOS header */
	fseek(status->fp, 60, SEEK_SET);
	/* Read offset to PE header */
	fread(&offset, 4, 1, status->fp);
	/* Jump to the fields that contain digital signature info */
	fseek(status->fp, offset+152, SEEK_SET);
	fread(&offset, 4, 1, status->fp);
	if (offset == 0)
		return -1;
    VS(_T("%s contains a digital signature\n"), status->archivename);
	return offset;
#else
	return -1;
#endif
}

/*
 * Open the archive
 * Sets f_archiveFile, f_pkgstart, f_tocbuff and f_cookie.
 */
int openArchive(ARCHIVE_STATUS *status)
{
#ifdef WIN32
	int i;
#endif
	int filelen;

	VS(_T("openArchive called.  Attempting to open %s\n"),status->archivename);

	/* Physically open the file */
	status->fp = _tfopen(status->archivename, _T("rb"));
	if (status->fp == NULL) {
		VS(_T("Cannot open archive: %s\n"), status->archivename);
		return -1;
	}

	/* Seek to the Cookie at the end of the file. */
	fseek(status->fp, 0, SEEK_END);
	filelen = ftell(status->fp);

	if (checkCookie(status, filelen) < 0)
	{
		VS(_T("inside of checkcookie\n"));

		VS(_T("%s does not contain an embedded package\n"), status->archivename); 
#ifndef WIN32
    return -1;
#else
		filelen = findDigitalSignature(status);
		if (filelen < 1)
			return -1;
		/* The digital signature has been aligned to 8-bytes boundary.
		   We need to look for our cookie taking into account some
		   padding. */
		for (i = 0; i < 8; ++i)
		{
			if (checkCookie(status, filelen) >= 0)
				break;
			--filelen;
		}
		if (i == 8)
		{
			VS(_T("%s does not contain an embedded package, even skipping the signature\n"), status->archivename);
			return -1;
		}
		VS(_T("package found skipping digital signature in %s\n"), status->archivename);
#endif
	}

	/* From the cookie, calculate the archive start */
	status->pkgstart = filelen - ntohl(status->cookie.len);

	/* Read in in the table of contents */
	fseek(status->fp, status->pkgstart + ntohl(status->cookie.TOC), SEEK_SET);
	status->tocbuff = (TOC *) malloc(ntohl(status->cookie.TOClen));
	if (status->tocbuff == NULL)
	{
		FATALERROR(_T("Could not allocate buffer for TOC."));
		return -1;
	}
	if (fread(status->tocbuff, ntohl(status->cookie.TOClen), 1, status->fp) < 1)
	{
	    FATALERROR(_T("Could not read from file."));
	    return -1;
	}
	status->tocend = (TOC *) (((char *)status->tocbuff) + ntohl(status->cookie.TOClen));

	/* Check input file is still ok (should be). */
	if (ferror(status->fp))
	{
		FATALERROR(_T("Error on file"));
		return -1;
	}
	return 0;
}
#ifndef WIN32
#define HMODULE void *
#define HINSTANCE void *
#endif

/*
 * Python versions before 2.4 do not export IncRef/DecRef as a binary API,
 * but only as macros in header files. Since we do not want to depend on
 * Python.h for many reasons (including the fact that we would like to
 * have a single binary for all Python versions), we provide an emulated
 * incref/decref here, that work on the binary layout of the PyObject
 * structure as it was defined in Python 2.3 and older versions.
 */
struct _old_typeobject;
typedef struct _old_object {
    int ob_refcnt;
    struct _old_typeobject *ob_type;
} OldPyObject;
typedef void (*destructor)(PyObject *);
typedef struct _old_typeobject {
    int ob_refcnt;
    struct _old_typeobject *ob_type;
    int ob_size;
    char *tp_name; /* For printing */
    int tp_basicsize, tp_itemsize; /* For allocation */
    destructor tp_dealloc;
    /* ignore the rest.... */
} OldPyTypeObject;

static void _EmulatedIncRef(PyObject *o)
{
    OldPyObject *oo = (OldPyObject*)o;
    if (oo)
        oo->ob_refcnt++;
}

static void _EmulatedDecRef(PyObject *o)
{
    #define _Py_Dealloc(op) \
        (*(op)->ob_type->tp_dealloc)((PyObject *)(op))

    OldPyObject *oo = (OldPyObject*)o;
    if (--(oo)->ob_refcnt == 0)
        _Py_Dealloc(oo);
}

int mapNames(HMODULE dll, int pyvers)
{
    /* Get all of the entry points that we are interested in */
    GETVAR(dll, Py_FrozenFlag);
    GETVAR(dll, Py_NoSiteFlag);
    GETVAR(dll, Py_OptimizeFlag);
    GETVAR(dll, Py_VerboseFlag);
    GETPROC(dll, Py_Initialize);
    GETPROC(dll, Py_Finalize);
    GETPROCOPT(dll, Py_IncRef);
    GETPROCOPT(dll, Py_DecRef);
    GETPROC(dll, PyImport_ExecCodeModule);
    GETPROC(dll, PyRun_SimpleString);
    GETPROC(dll, PyString_FromStringAndSize);
    GETPROC(dll, PySys_SetArgv);
    GETPROC(dll, Py_SetProgramName);
    GETPROC(dll, PyImport_ImportModule);
    GETPROC(dll, PyImport_AddModule);
    GETPROC(dll, PyObject_SetAttrString);
    GETPROC(dll, PyList_New);
    GETPROC(dll, PyList_Append);
    GETPROC(dll, Py_BuildValue);
    GETPROC(dll, PyFile_FromString);
    GETPROC(dll, PyString_AsString);
    GETPROC(dll, PyObject_CallFunction);
    GETPROC(dll, PyModule_GetDict);
    GETPROC(dll, PyDict_GetItemString);
    GETPROC(dll, PyErr_Clear);
    GETPROC(dll, PyErr_Occurred);
    GETPROC(dll, PyErr_Print);
    GETPROC(dll, PyObject_CallObject);
    GETPROC(dll, PyObject_CallMethod);
    GETPROC(dll, PySys_AddWarnOption);
    GETPROC(dll, PyEval_InitThreads);
    GETPROC(dll, PyEval_AcquireThread);
    GETPROC(dll, PyEval_ReleaseThread);
    GETPROC(dll, PyThreadState_Swap);
    GETPROC(dll, Py_NewInterpreter);
    GETPROC(dll, Py_EndInterpreter);
    GETPROC(dll, PyInt_AsLong);
    GETPROC(dll, PySys_SetObject);
	GETPROC(dll, PyObject_GetAttr);
	GETPROC(dll, PyString_FromString);
	GETPROC(dll, PyUnicodeUCS2_FromUnicode);  
	GETPROC(dll, PyUnicodeUCS4_FromUnicode);  

    if (!PI_Py_IncRef) PI_Py_IncRef = _EmulatedIncRef;
    if (!PI_Py_DecRef) PI_Py_DecRef = _EmulatedDecRef;

    return 0;
}

/*
 * Load the Python DLL, and get all of the necessary entry points
 */
int loadPython(ARCHIVE_STATUS *status)
{
	HINSTANCE dll;
	TCHAR dllpath[_MAX_PATH + 1];
    int pyvers = ntohl(status->cookie.pyvers);

#ifdef WIN32
	/* Determine the path */
	
	_stprintf(dllpath, _T("%spython%02d.dll"), status->homepathraw, pyvers);
	VS(_T("PYTHON PATH ATTEMPTED: %s\n"),dllpath);

	/* Load the DLL */
	dll = LoadLibraryEx(dllpath, NULL, LOAD_WITH_ALTERED_SEARCH_PATH); 
	if (dll) {
		VS(_T("%s\n"), dllpath);
	}
	else {
		_stprintf(dllpath, _T("%spython%02d.dll"), status->temppathraw, pyvers);
		dll = LoadLibraryEx(dllpath, NULL, LOAD_WITH_ALTERED_SEARCH_PATH );
		if (dll) {
			VS(_T("%s\n"), dllpath);
		}
	}
	if (dll == 0) {
		FATALERROR(_T("Error loading Python DLL: %s (error code %d)\n"),
			dllpath, GetLastError());
		return -1;
	}

	mapNames(dll, pyvers);
#else

	/* Determine the path */
#ifdef __APPLE__

    /* Try to load python library both from temppath and homepath */
	if (checkFile(dllpath, _T("%sPython"), status->temppath) != 0) {
        if (checkFile(dllpath, _T("%sPython"), status->homepath) != 0) {
            if (checkFile(dllpath, _T("%s.Python"), status->temppath) != 0){
                if (checkFile(dllpath, _T("%s.Python"), status->homepath) != 0){
                    FATALERROR(_T("Python library not found."));
                    return -1;
                }
            }
        }
    }
#else
    if (checkFile(dllpath, _T("%slibpython%01d.%01d.so.1.0"), status->temppath, pyvers / 10, pyvers % 10) != 0) {
        if (checkFile(dllpath, _T("%slibpython%01d.%01d.so.1.0"), status->homepath, pyvers / 10, pyvers % 10) != 0) {
            FATALERROR(_T("Python library not found."));
            return -1;
        }
    }
#endif

	/* Load the DLL */
	dll = dlopen(dllpath, RTLD_NOW|RTLD_GLOBAL);
	if (dll) {
		VS(_T("%s\n"), dllpath);
	}
	if (dll == 0) {
		FATALERROR(_T("Error loading Python lib '%s': %s\n"),
			dllpath, dlerror());
		return -1;
	}

	mapNames(dll, pyvers);

#endif

	return 0;
}

/*
 * use this from a dll instead of loadPython()
 * it will attach to an existing pythonXX.dll,
 * or load one if needed.
 */
int attachPython(ARCHIVE_STATUS *status, int *loadedNew)
{
#ifdef WIN32
	HMODULE dll;
	TCHAR nm[_MAX_PATH + 1];
    int pyvers = ntohl(status->cookie.pyvers);

	/* Get python's name */
	_stprintf(nm, _T("python%02d.dll"), pyvers);

	/* See if it's loaded */
	dll = GetModuleHandle(nm); // UNICODE: was "A"
	if (dll == 0) {
		*loadedNew = 1;
		return loadPython(status);
	}
	mapNames(dll, pyvers);
	*loadedNew = 0;
#endif
	return 0;
}

/*
 * Return pointer to next toc entry.
 */
TOC *incrementTocPtr(ARCHIVE_STATUS *status, TOC* ptoc)
{
	TOC *result = (TOC*)((char *)ptoc + ntohl(ptoc->structlen));
	if (result < status->tocbuff) {
		FATALERROR(_T("Cannot read Table of Contents.\n"));
		return status->tocend;
	}
	return result;
}
/*
 * external API for iterating TOCs
 */
TOC *getFirstTocEntry(ARCHIVE_STATUS *status)
{
	return status->tocbuff;
}
TOC *getNextTocEntry(ARCHIVE_STATUS *status, TOC *entry)
{
	TOC *rslt = (TOC*)((char *)entry + ntohl(entry->structlen));
	if (rslt >= status->tocend)
		return NULL;
	return rslt;
}
/*
 * A toc entry of type 'o' holds runtime options
 * toc->name is the arg
 * this is so you can freeze in command line args to Python
 */
int setRuntimeOptions(ARCHIVE_STATUS *status)
{
	int unbuffered = 0;
	TOC *ptoc = status->tocbuff;
	while (ptoc < status->tocend) {
		if (ptoc->typcd == 'o') {
			VSA("%s\n", ptoc->name);
			switch (ptoc->name[0]) {
			case 'v':
				*PI_Py_VerboseFlag = 1;
			    break;
			case 'u':
				unbuffered = 1;
			    break;
			case 'W':
                PI_PySys_AddWarnOption(&ptoc->name[2]);
			    break;
			case 's':
				*PI_Py_NoSiteFlag = 0;
			    break;
			case 'O':
				*PI_Py_OptimizeFlag = 1;
			    break;
			}
		}
		ptoc = incrementTocPtr(status, ptoc);
	}
	if (unbuffered) {
#ifdef WIN32
		_setmode(fileno(stdin), O_BINARY);
		_setmode(fileno(stdout), O_BINARY);
#else
		fflush(stdout);
		fflush(stderr);

		setbuf(stdin, (char *)NULL);
		setbuf(stdout, (char *)NULL);
		setbuf(stderr, (char *)NULL);
#endif
	}
	return 0;
}



int insertSearchPath(PyObject*sys,TCHAR *pth)
{
	PyObject *ppth;
	PyObject *attr;
	PyObject *sysdotpath;

	VS(_T("Adding search path to sys.path: %s\n"),pth);   fflush(stdout);

#ifdef UNICODE
	// ASSUMPTION: unicode on the C side is the same as the Python side.  For Windows, I think
    // this is true.  The others, I doubt it.  See http://docs.python.org/c-api/unicode.html.

	if (!PI_PyUnicodeUCS2_FromUnicode && !PI_PyUnicodeUCS4_FromUnicode)
	{
		printf("FATAL: no PyUnicode_FromUnicode function available.  It could be that that the call signature assumed in PyInstaller is incorrect.\n");
		printf("       See source/launch.c and source/launch.h and search for FromUnicode.\n");
		exit(1);
	}
	if (PI_PyUnicodeUCS2_FromUnicode)
	    ppth = PI_PyUnicodeUCS2_FromUnicode(pth,_tcslen(pth));
	else
		ppth = PI_PyUnicodeUCS4_FromUnicode(pth,_tcslen(pth));
	
#else
	ppth = PI_PyString_FromString(pth);
#endif
	attr = PI_PyString_FromString("path");
	
	sysdotpath = PI_PyObject_GetAttr(sys,attr);

	PI_PyList_Append(sysdotpath,ppth);

	PI_Py_DecRef(ppth);
	PI_Py_DecRef(attr);

	return 0;
}


/*
 * Start python - return 0 on success
 */
int startPython(ARCHIVE_STATUS *status, int argc, char *argv[])
{
	char itemtype[3];
    /* Set PYTHONPATH so dynamic libs will load */
	static TCHAR pypath[2*_MAX_PATH + 14];
	int pathlen = 1;
	int i;
	TCHAR cmd[_MAX_PATH+1+80];
	TCHAR tmp[_MAX_PATH+1];
	PyObject *py_argv;
	PyObject *val;
	PyObject *sys;

    /* Set the PYTHONPATH */
	VS(_T("Manipulating evironment\n"));
	_tcscpy(pypath, _T("PYTHONPATH="));
    if (status->temppath[0] != _T('\0')) { /* Temppath is set */
	    _tcscat(pypath, status->temppath);
	    pypath[_tcslen(pypath)-1] = _T('\0'); 
	    _tcscat(pypath, PATHSEP);
    }
	_tcscat(pypath, status->homepath);

	/* don't chop off SEP if root directory */
#ifdef WIN32
	if (_tcslen(pypath) > 14)
#else
	if (_tcslen(pypath) > 12)
#endif
		pypath[_tcslen(pypath)-1] = _T('\0'); 

	_tputenv(pypath); 
	VS(_T("%s\n"), pypath);
	/* Clear out PYTHONHOME to avoid clashing with any installation */
#ifdef WIN32
	_tputenv(_T("PYTHONHOME="));
#endif

	/* Start python. */
	/* VS("Loading python\n"); */
	*PI_Py_NoSiteFlag = 1;	/* maybe changed to 0 by setRuntimeOptions() */
    *PI_Py_FrozenFlag = 1;
	setRuntimeOptions(status);
	PI_Py_SetProgramName(status->archivename); /*XXX*/    // PROBLEM: archivename is Unicode...how does this work????? or maybe it doesn't?
	PI_Py_Initialize();

	// import sys
	VS(_T("Importing sys...\n"));  fflush(stdout);
	sys = PI_PyImport_ImportModule("sys");


	/* Set sys.path */
	VS(_T("Manipulating Python's sys.path\n"));   fflush(stdout);
	PI_PyRun_SimpleString("import sys\n");
	PI_PyRun_SimpleString("del sys.path[:]\n"); // TODO: why not call a Python API to both import and del sys.path[:]? 

    if (status->temppath[0] != _T('\0')) {
        _tcscpy(tmp, status->temppath);
	    tmp[_tcslen(tmp)-1] = _T('\0');
	    //_stprintf(cmd, "sys.path.append(r\"%s\")", tmp);
        //PI_PyRun_SimpleString(cmd); // PROBLEM UNICODE: how to I run a unicode string???		
		insertSearchPath(sys,tmp);
    }

	_tcscpy(tmp, status->homepath);
	tmp[_tcslen(tmp)-1] = _T('\0');
	insertSearchPath(sys,tmp);
	//_stprintf(cmd, _T("sys.path.append(r\"%s\")"), tmp);
	//PI_PyRun_SimpleString (cmd);

	/* Set argv[0] to be the archiveName */
#ifdef UNICODE
	strcpy(itemtype,"u");
#else
	strcpy(itemtype,"s");
#endif
	py_argv = PI_PyList_New(0);
    //val = PI_Py_BuildValue("s", status->archivename);  
	val = PI_Py_BuildValue(itemtype, status->archivename);  // UNICODECONCERN: I guess the first item of argv being unicode and the rest ascii is appropriate at this point?
	PI_PyList_Append(py_argv, val);
	for (i = 1; i < argc; ++i) {
		val = PI_Py_BuildValue ("s", argv[i]); // UNICODE: replace this with 'itemtype' if you want to pass unicode in the list.  Needs investigation.
		PI_PyList_Append (py_argv, val);
	}
	
	/* VS("Setting sys.argv\n"); */
	PI_PyObject_SetAttrString(sys, "argv", py_argv);

	/* Check for a python error */
	if (PI_PyErr_Occurred())
	{
		FATALERROR(_T("Error detected starting Python VM."));
		return -1;
	}

	return 0;
}

/*
 * Import modules embedded in the archive - return 0 on success
 */
int importModules(ARCHIVE_STATUS *status)
{
	PyObject *marshal;
	PyObject *marshaldict;
	PyObject *loadfunc;
	TOC *ptoc;
	PyObject *co;
	PyObject *mod;

	VS(_T("importing modules from CArchive\n"));

	/* Get the Python function marshall.load
		* Here we collect some reference to PyObject that we don't dereference
		* Doesn't matter because the objects won't be going away anyway.
		*/
	marshal = PI_PyImport_ImportModule("marshal");
	marshaldict = PI_PyModule_GetDict(marshal);
	loadfunc = PI_PyDict_GetItemString(marshaldict, "loads");

	/* Iterate through toc looking for module entries (type 'm')
		* this is normally just bootstrap stuff (archive and iu)
		*/
	ptoc = status->tocbuff;
	while (ptoc < status->tocend) {
		if (ptoc->typcd == 'm' || ptoc->typcd == 'M')
		{
			unsigned char *modbuf = extract(status, ptoc);

			VSA("extracted %s\n", ptoc->name);

			/* .pyc/.pyo files have 8 bytes header. Skip it and load marshalled
			 * data form the right point.
			 */
			co = PI_PyObject_CallFunction(loadfunc, "s#", modbuf+8, ntohl(ptoc->ulen)-8);
			mod = PI_PyImport_ExecCodeModule(ptoc->name, co);

			/* Check for errors in loading */
			if (mod == NULL) {
				FATALERROR(_T("mod is NULL - %s"), ptoc->name);
			}
			if (PI_PyErr_Occurred())
			{
				PI_PyErr_Print();
				PI_PyErr_Clear();
			}

			free(modbuf);
		}
		ptoc = incrementTocPtr(status, ptoc);
	}

	return 0;
}


/* Install a zlib from a toc entry
 * Return non zero on failure
 */
int installZlib(ARCHIVE_STATUS *status, TOC *ptoc)
{
	int rc;
	int zlibpos = status->pkgstart + ntohl(ptoc->pos);
#ifndef UNICODE // TODO remove this in favor of that is below.
	char *tmpl = "sys.path.append(r\"%s?%d\")\n";
	char *cmd = (char *) malloc(strlen(tmpl) + strlen(status->archivename) + 32);
	sprintf(cmd, tmpl, status->archivename, zlibpos);
	VS(cmd);
	rc = PI_PyRun_SimpleString(cmd);
	
#else
	PyObject *sys;
	TCHAR pth[_MAX_PATH*2];
	sys = PI_PyImport_ImportModule("sys");
	_stprintf(pth,_T("%s?%d"),status->archivename,zlibpos);

	insertSearchPath(sys,pth);
	PI_Py_DecRef(sys);
#endif

	// TODO error detection
	//if (rc != 0)
	//{
	//	FATALERROR(_(T"Error in command: %s\n"), cmd);
	//	free(cmd);
	//	return -1;
	//}

	//free(cmd);
	return 0;
}


/*
 * Install zlibs
 * Return non zero on failure
 */
int installZlibs(ARCHIVE_STATUS *status)
{
	TOC * ptoc;
	VS(_T("Installing import hooks\n"));

	/* Iterate through toc looking for zlibs (type 'z') */
	ptoc = status->tocbuff;
	while (ptoc < status->tocend) {
		if (ptoc->typcd == 'z')
		{
			VSA("installZlibs: ptoc->name = %s\n", ptoc->name);
			installZlib(status, ptoc);
		}

		ptoc = incrementTocPtr(status, ptoc);
	}

	printf("After intalling the zlibs, the path is now:\n");
	PI_PyRun_SimpleString("for i in sys.path: print \"  ==>\" + repr(i)");

	return 0;
}

/* decompress data in buff, described by ptoc
 * return in malloc'ed buffer (needs to be freed)
 */
unsigned char *decompress(unsigned char * buff, TOC *ptoc)
{
	const char *ver;
	unsigned char *out;
	z_stream zstream;
	int rc;

	ver = (zlibVersion)();
	out = (unsigned char *)malloc(ntohl(ptoc->ulen));
	if (out == NULL) {
		OTHERERROR("Error allocating decompression buffer\n");
		return NULL;
	}

	zstream.zalloc = NULL;
	zstream.zfree = NULL;
	zstream.opaque = NULL;
	zstream.next_in = buff;
	zstream.avail_in = ntohl(ptoc->len);
	zstream.next_out = out;
	zstream.avail_out = ntohl(ptoc->ulen);
	rc = inflateInit(&zstream);
	if (rc >= 0) {
		rc = (inflate)(&zstream, Z_FINISH);
		if (rc >= 0) {
			rc = (inflateEnd)(&zstream);
		}
		else {
			OTHERERROR(_T("Error %d from inflate: %s\n"), rc, zstream.msg);
			return NULL;
		}
	}
	else {
		OTHERERROR(_T("Error %d from inflateInit: %s\n"), rc, zstream.msg);
		return NULL;
	}

	return out;
}

/*
 * extract an archive entry
 * returns pointer to the data (must be freed)
 */
unsigned char *extract(ARCHIVE_STATUS *status, TOC *ptoc)
{
	unsigned char *data;
	unsigned char *tmp;

	fseek(status->fp, status->pkgstart + ntohl(ptoc->pos), SEEK_SET);
	data = (unsigned char *)malloc(ntohl(ptoc->len));
	if (data == NULL) {
		OTHERERROR(_T("Could not allocate read buffer\n"));
		return NULL;
	}
	if (fread(data, ntohl(ptoc->len), 1, status->fp) < 1) {
	    OTHERERROR(_T("Could not read from file\n"));
	    return NULL;
	}
	if (ptoc->cflag == '\2') {
        static PyObject *AES = NULL;
		PyObject *func_new;
		PyObject *aes_dict;
		PyObject *aes_obj;
		PyObject *ddata;
		long block_size;
		char *iv;

		if (!AES)
			AES = PI_PyImport_ImportModule("AES");
		aes_dict = PI_PyModule_GetDict(AES);
		func_new = PI_PyDict_GetItemString(aes_dict, "new");
		block_size = PI_PyInt_AsLong(PI_PyDict_GetItemString(aes_dict, "block_size"));
		iv = malloc(block_size);
		memset(iv, 0, block_size);

		aes_obj = PI_PyObject_CallFunction(func_new, "s#Os#",
			data, 32,
			PI_PyDict_GetItemString(aes_dict, "MODE_CFB"),
			iv, block_size);

		ddata = PI_PyObject_CallMethod(aes_obj, "decrypt", "s#", data+32, ntohl(ptoc->len)-32);
		memcpy(data, PI_PyString_AsString(ddata), ntohl(ptoc->len)-32);
		Py_DECREF(aes_obj);
		Py_DECREF(ddata);
		VS(_T("decrypted %s\n"), ptoc->name);
	}
	if (ptoc->cflag == '\1' || ptoc->cflag == '\2') {
		tmp = decompress(data, ptoc);
		free(data);
		data = tmp;
		if (data == NULL) {
			OTHERERROR(_T("Error decompressing %s\n"), ptoc->name);
			return NULL;
		}
	}
	return data;
}

/*
 * helper for extract2fs
 * which may try multiple places
 */
FILE *openTarget(const TCHAR *path, const TCHAR* name_)
{
	struct stat sbuf;
	TCHAR fnm[_MAX_PATH+1];
	TCHAR name[_MAX_PATH+1];
	TCHAR *dir;

	VS(_T("openTarget: %s %s\n"),path,name_);

	_tcscpy(fnm, path);
	_tcscpy(name, name_);
	fnm[_tcslen(fnm)-1] = _T('\0'); // knock off the slash at the end

	dir = _tcstok(name, _T("/\\")); 
	while (dir != NULL)
	{
#ifdef WIN32
		_tcscat(fnm, _T("\\"));
#else
		_tcscat(fnm, _T("/"));
#endif
		_tcscat(fnm, dir);
		dir = _tcstok(NULL, _T("/\\"));
		if (!dir)
			break;
		if (_tstat(fnm, &sbuf) < 0)
    {
#ifdef WIN32
			_tmkdir(fnm);
#else
			_tmkdir(fnm, 0700);
#endif
    }
	}

	if (_tstat(fnm, &sbuf) == 0) {
		OTHERERROR(_T("WARNING: file already exists but should not: %s\n"), fnm);
    }
	return _tfopen(fnm, _T("wb"));
}

/* Function that creates a temporany directory if it doesn't exists
 *  and properly sets the ARCHIVE_STATUS members.
 */
static int createTempPath(ARCHIVE_STATUS *status)
{
#ifdef WIN32
	TCHAR *p;
#endif

	if (status->temppath[0] == _T('\0')) {
		if (!getTempPath(status->temppath))
		{
            FATALERROR(_T("INTERNAL ERROR: cannot create temporary directory!\n"));
            return -1;
		}
#ifdef WIN32
		_tcscpy(status->temppathraw, status->temppath);
		BackslashToFrontslash(status->temppath);
		VS(_T("temppath (in createTempPath) set to %s\n"),status->temppath);
#endif
	}
    return 0;
}

// TODO: split this into a platform-specific utility function.
// kind of like a strncpy, but promotes ascii to unicode.
// PROBLEM: windows specific, with no corresponding code for Linux/OSX yet.
//
// if nascii is -1, it copies all characters in txta up to and including the null terminator.
void ascii_to_unicode(TCHAR * txtu,const char *txta,int txtu_len,int nascii)
{
#ifdef UNICODE
#ifdef WIN32
	MultiByteToWideChar(CP_ACP,0,txta,nascii,txtu,txtu_len);
#else	
	if (nascii == -1) nascii = strlen(txta) + 1;
	strncpy(txtu,txta,nascii);
#endif	
#else
	if (nascii == -1) nascii = strlen(txta) + 1;
	strncpy(txtu,txta,nascii);
#endif

}



/*
 * extract from the archive
 * and copy to the filesystem
 * relative to the directory the archive's in
 */
int extract2fs(ARCHIVE_STATUS *status, TOC *ptoc)
{
	FILE *out;
	TCHAR thename[_MAX_PATH];

	unsigned char *data = extract(status, ptoc);

    if (createTempPath(status) == -1){
        return -1;
    }
	ascii_to_unicode(thename,ptoc->name,_MAX_PATH,-1);

	_tprintf(_T("ptoc->name(wide) = %s\n"),thename);

	out = openTarget(status->temppath, thename);

	if (out == NULL)  {
		FATALERROR(_T("%s could not be extracted!\n"), ptoc->name);
		return -1;
	}
	else {
		fwrite(data, ntohl(ptoc->ulen), 1, out);
#ifndef WIN32
		fchmod(fileno(out), S_IRUSR | S_IWUSR | S_IXUSR);
#endif
		fclose(out);
	}
	free(data);
	return 0;
}

/* Splits the item in the form path:filename */
// UNICODE note.  In the usage of this function, "item" is a name in the archive, which is currently a char.
// From what I can tell, what gets passed in here is something like "test1_multipackage_B.exe:_socket.pyd".  So
// no paths, which means we can keep this ascii.  For now.
static int splitName(char *path, char *filename, const char *item)
{
    char name[_MAX_PATH + 1];

    VSA("Splitting item into path and filename: %s\n",item);
	fflush(stdout);

    strcpy(name, item);
    strcpy(path, strtok(name, _T(":")));
    strcpy(filename, strtok(NULL, _T(":"))) ;

    if (path[0] == 0 || filename[0] == 0)
        return -1;

    return 0;
}

/* Copy the file src to dst 4KB per time */
static int copyFile(const TCHAR *src, const TCHAR *dst, const TCHAR *filename)
{
    FILE *in = _tfopen(src, _T("rb"));
    FILE *out = openTarget(dst, filename);
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

/* Giving a fullpath, returns a newly allocated string
 * which contains the directory name.
 * The returned string must be freed after use.
 */
// UNICODE: the name of this function seems to indicate that it is meant for more than it does.
// "fullpath" is really just a filename, at least as far as I can tell at this point.  UNICODECONCERN.
static TCHAR *dirName(const char *fullpath)
{
    char *match = strrchr(fullpath, SEPA);
    TCHAR *pathname = (TCHAR *) calloc(_MAX_PATH, sizeof(TCHAR));
    VS(_T("Calculating dirname from fullpath\n"));
    if (match != NULL) {
		VS(_T("WARNING: match was nonnull, and I never thought it would be!\n"));
		ascii_to_unicode(pathname,fullpath,_MAX_PATH,match-fullpath+1);
        //_tcsncpy(pathname, fullpath, match - fullpath + 1);
	}
    else
	{
		ascii_to_unicode(pathname,fullpath,_MAX_PATH,-1);
        //_tcscpy(pathname, fullpath);
	}

    VS(_T("Pathname: %s\n"), pathname);
    return pathname;
}

/* Copy the dependencies file from a directory to the tempdir */
static int copyDependencyFromDir(ARCHIVE_STATUS *status, const TCHAR *srcpath, const TCHAR *filename)
{
    if (createTempPath(status) == -1){
        return -1;
    }

    VS(_T("Copying file %s to %s\n"), srcpath, status->temppath);
    if (copyFile(srcpath, status->temppath, filename) == -1) {
        return -1;
    }
    return 0;
}

/* Look for the archive identified by path into the ARCHIVE_STATUS pool status_list.
 * If the archive is found, a pointer to the associated ARCHIVE_STATUS is returned
 * otherwise the needed archive is opened and added to the pool and then returned.
 * If an error occurs, returns NULL.
 */
static ARCHIVE_STATUS *get_archive(ARCHIVE_STATUS *status_list[], const char *path)
{
    ARCHIVE_STATUS *status = NULL;
    int i = 0;

    VS(_T("Getting file from archive.\n"));
    if (createTempPath(status_list[SELF]) == -1){
        return NULL;
    }

    for (i = 1; status_list[i] != NULL; i++){
        if (strcmp(status_list[i]->archivename, path) == 0) {
            VS(_T("Archive found: %s\n"), path);
            return status_list[i];
        }
        VS(_T("Checking next archive in the list...\n"));
    }

    if ((status = (ARCHIVE_STATUS *) calloc(1, sizeof(ARCHIVE_STATUS))) == NULL) {
        FATALERROR(_T("Error allocating memory for status\n"));
        return NULL;
    }

    _tcscpy(status->archivename, path);
    _tcscpy(status->homepath, status_list[SELF]->homepath);
    _tcscpy(status->temppath, status_list[SELF]->temppath);
#ifdef WIN32
    _tcscpy(status->homepathraw, status_list[SELF]->homepathraw);
    _tcscpy(status->temppathraw, status_list[SELF]->temppathraw);
#endif

    if (openArchive(status)) {
        FATALERROR(_T("Error opening archive %s\n"), path);
        free(status);
        return NULL;
    }

    status_list[i] = status;
    return status;
}

/* Extract a file identifed by filename from the archive associated to status. */
static int extractDependencyFromArchive(ARCHIVE_STATUS *status, const char *filename)
{
	TOC * ptoc = status->tocbuff;
	VS(_T("Extracting dependencies from archive\n"));
	while (ptoc < status->tocend) {
		if (strcmp(ptoc->name, filename) == 0)  
			if (extract2fs(status, ptoc))
				return -1;
		ptoc = incrementTocPtr(status, ptoc);
	}
	return 0;
}




/* Decide if the dependency identified by item is in a onedir or onefile archive
 * then call the appropriate function.
 */
static int extractDependency(ARCHIVE_STATUS *status_list[], const char *item)
{
    ARCHIVE_STATUS *status = NULL;
    char path[_MAX_PATH + 1];
	TCHAR pathu[_MAX_PATH + 1];
    char filename[_MAX_PATH + 1];
	TCHAR filenameu[_MAX_PATH + 1];
    TCHAR srcpath[_MAX_PATH + 1];
    TCHAR archive_path[_MAX_PATH + 1];
    TCHAR *dirname = NULL;

	VSA("Extracting dependencies for: %s\n",item);

    if (splitName(path, filename, item) == -1)
        return -1;

    dirname = dirName(path); // unicode note.  path going in is a char.  What is return is unicode.
    if (dirname[0] == _T('\0')) {
        free(dirname);
        return -1;
    }

    /* We need to identify three situations: 1) dependecies are in a onedir archive
     * next to the current onefile archive, 2) dependencies are in a onedir/onefile
     * archive next to the current onedir archive, 3) dependencies are in a onefile
     * archive next to the current onefile archive.
     */
    VS(_T("Checking if file exists\n"));

	ascii_to_unicode(filenameu,filename,_MAX_PATH,-1);
	ascii_to_unicode(pathu,path,_MAX_PATH,-1);

	VS(_T("PRE %s|%s|%s\n"), status_list[SELF]->homepath, dirname,filenameu);
	
	
    if (checkFile(srcpath, _T("%s/%s/%s"), status_list[SELF]->homepath, dirname, filenameu) == 0) {
        VS(_T("File %s found, assuming is onedir\n"), srcpath);
        if (copyDependencyFromDir(status_list[SELF], srcpath, filenameu) == -1) {
            FATALERROR(_T("Error copying %s\n"), filenameu);
            free(dirname);
            return -1;
        }
    } else if (checkFile(srcpath, _T("%s../%s/%s"), status_list[SELF]->homepath, dirname, filenameu) == 0) {
        VS(_T("File %s found, assuming is onedir\n"), srcpath);
        if (copyDependencyFromDir(status_list[SELF], srcpath, filenameu) == -1) {
            FATALERROR(_T("Error copying %s\n"), filenameu);
            free(dirname);
            return -1;
        }
    } else {
        VS(_T("File %s not found, assuming is onefile.\n"), srcpath);

        if ((checkFile(archive_path, _T("%s%s.pkg"), status_list[SELF]->homepath, pathu) != 0) &&
            (checkFile(archive_path, _T("%s%s.exe"), status_list[SELF]->homepath, pathu) != 0) &&
            (checkFile(archive_path, _T("%s%s"), status_list[SELF]->homepath, pathu) != 0)) {
            FATALERROR(_T("Archive not found: %s\n"), archive_path);
            return -1;
        }

        if ((status = get_archive(status_list, archive_path)) == NULL) {
            FATALERROR(_T("Archive not found: %s\n"), archive_path);
            return -1;
        }

        if (extractDependencyFromArchive(status, filename) == -1) { 
            FATALERROR(_T("Error extracting %s\n"), filenameu);
            free(status);
            return -1;
        }
    }
    free(dirname);

    return 0;
}

/*
 * extract all binaries (type 'b') and all data files (type 'x') to the filesystem
 * and checks for dependencies (type 'd'). If dependencies are found, extract them.
 */
int extractBinaries(ARCHIVE_STATUS *status_list[])
{
	TOC * ptoc = status_list[SELF]->tocbuff;
	VS(_T("Extracting binaries\n"));
	while (ptoc < status_list[SELF]->tocend) {
		if (ptoc->typcd == 'b' || ptoc->typcd == 'x' || ptoc->typcd == 'Z')
			if (extract2fs(status_list[SELF], ptoc))
				return -1;

        if (ptoc->typcd == 'd') {
			printf("IN EXTRACTBINARIES: %d\n",ptoc->name);
            if (extractDependency(status_list, ptoc->name) == -1)
                return -1;
        }
		ptoc = incrementTocPtr(status_list[SELF], ptoc);
	}
	VS(_T("Finished extracting binaries\n"));
	return 0;
}

/*
 * Run scripts
 * Return non zero on failure
 */
int runScripts(ARCHIVE_STATUS *status)
{
	unsigned char *data;
	char buf[_MAX_PATH];
	int rc = 0;
	TOC * ptoc = status->tocbuff;
	PyObject *__main__ = PI_PyImport_AddModule("__main__");
	PyObject *__file__;
	VS(_T("Running scripts\n"));

	/*
	 * Now that the startup is complete, we can reset the _MEIPASS2 env
	 * so that if the program invokes another PyInstaller one-file program
	 * as subprocess, this subprocess will not fooled into thinking that it
	 * is already unpacked.
	 */
	unsetenv(_T("_MEIPASS2")); 

	/* Iterate through toc looking for scripts (type 's') */
	while (ptoc < status->tocend) {
		if (ptoc->typcd == 's') {
			/* Get data out of the archive.  */
			data = extract(status, ptoc);
			/* Set the __file__ attribute within the __main__ module,
			   for full compatibility with normal execution. */
			strcpy(buf, ptoc->name);
			strcat(buf, ".py");
            __file__ = PI_PyString_FromStringAndSize(buf, strlen(buf));
            PI_PyObject_SetAttrString(__main__, "__file__", __file__);
            Py_DECREF(__file__);
			/* Run it */
			printf("ABOUT TO RUN THIS IN THE INTERPRETER\n");
			printf("%s\n",data);
			rc = PI_PyRun_SimpleString(data);
			/* log errors and abort */
			if (rc != 0) {
				VSA("RC: %d from %s\n", rc, ptoc->name); 
				return rc;
			}
			free(data);
		}

		ptoc = incrementTocPtr(status, ptoc);
	}
	return 0;
}

/*
 * call a simple "int func(void)" entry point.  Assumes such a function
 * exists in the main namespace.
 * Return non zero on failure, with -2 if the specific error is
 * that the function does not exist in the namespace.
 */
int callSimpleEntryPoint(char *name, int *presult)
{
	int rc = -1;
	/* Objects with no ref. */
	PyObject *mod, *dict;
	/* Objects with refs to kill. */
	PyObject *func = NULL, *pyresult = NULL;

	mod = PI_PyImport_AddModule("__main__"); /* NO ref added */
	if (!mod) {
		VS(_T("No __main__\n"));
		goto done;
	}
	dict = PI_PyModule_GetDict(mod); /* NO ref added */
	if (!mod) {
		VS(_T("No __dict__\n"));
		goto done;
	}
	func = PI_PyDict_GetItemString(dict, name);
	if (func == NULL) { /* should explicitly check KeyError */
		VS(_T("CallSimpleEntryPoint can't find the function name\n"));
		rc = -2;
		goto done;
	}
	pyresult = PI_PyObject_CallFunction(func, "");
	if (pyresult==NULL) goto done;
	PI_PyErr_Clear();
	*presult = PI_PyInt_AsLong(pyresult);
	rc = PI_PyErr_Occurred() ? -1 : 0;
	VS( rc ? _T("Finished with failure\n" : "Finished OK\n"));
	/* all done! */
done:
	Py_XDECREF(func);
	Py_XDECREF(pyresult);
	/* can't leave Python error set, else it may
	   cause failures in later async code */
	if (rc)
		/* But we will print them 'cos they may be useful */
		PI_PyErr_Print();
	PI_PyErr_Clear();
	return rc;
}

/* for finer grained control */
/*
 * initialize (this always needs to be done)
 */
int init(ARCHIVE_STATUS *status, TCHAR const * archivePath, TCHAR const * archiveName)
{
	VS(_T("INIT: archivepath = %s\n"),archivePath);
	VS(_T("INIT: archivename = %s\n"),archiveName);

	/* Set up paths */
	if (setPaths(status, archivePath, archiveName))
		return -1;

	/* Open the archive */
	if (openArchive(status))
		return -1;

	return 0;
}

/* once init'ed, you might want to extractBinaries()
 * If you do, what comes after is very platform specific.
 * Once you've taken care of the platform specific details,
 * or if there are no binaries to extract, you go on
 * to doIt(), which is the important part
 */
int doIt(ARCHIVE_STATUS *status, int argc, char *argv[])
{
	int rc = 0;

	VS(_T("LOADPYTHON\n")); fflush(stdout);
	/* Load Python DLL */
	if (loadPython(status))
		return -1;

	VS(_T("STARTPYTHON\n"));fflush(stdout);
	/* Start Python. */
	if (startPython(status, argc, argv))
		return -1;

	VS(_T("IMPORTMODULES\n"));fflush(stdout);
	/* Import modules from archive - bootstrap */
	if (importModules(status))
		return -1;

	VS(_T("INSTALLZLIBS\n"));fflush(stdout);
	/* Install zlibs  - now all hooks in place */
	if (installZlibs(status))
		return -1;

	/* Run scripts */
	VS(_T("RUNSCRIPTS\n"));fflush(stdout);
	rc = runScripts(status);

	VS(_T("OK.\n"));

	return rc;
}

void clear(const char *dir);
#ifdef WIN32
// UNICODE PROBLEM: NEEDS TO BE ADDRESSED
void removeOne(TCHAR *fnm, int pos, struct _finddata_t finfo)
{
	if ( strcmp(finfo.name, ".")==0  || strcmp(finfo.name, "..") == 0 )
		return;
	fnm[pos] = '\0';
	strcat(fnm, finfo.name);
	if ( finfo.attrib & _A_SUBDIR )
		clear(fnm);
	else if (remove(fnm)) {
        /* HACK: Possible concurrency issue... spin a little while */
        Sleep(100);
        remove(fnm);
    }
}

// UNICODE PROBLEM
void clear(const TCHAR *dir)
{
	TCHAR fnm[_MAX_PATH+1];
	struct _finddata_t finfo;
	long h;
	int dirnmlen;
	_tcscpy(fnm, dir);
	dirnmlen = _tcslen(fnm);
	if ( fnm[dirnmlen-1] != '/' && fnm[dirnmlen-1] != '\\' ) {
		strcat(fnm, "\\");
		dirnmlen++;
	}
	strcat(fnm, "*");
	h = _findfirst(fnm, &finfo);
	if (h != -1) {
		removeOne(fnm, dirnmlen, finfo);
		while ( _findnext(h, &finfo) == 0 )
			removeOne(fnm, dirnmlen, finfo);
		_findclose(h);
	}
	rmdir(dir);
}
#else
// UNICODE PROBLEM
void removeOne(char *pnm, int pos, const char *fnm)
{
	struct stat sbuf;
	if ( strcmp(fnm, ".")==0  || strcmp(fnm, "..") == 0 )
		return;
	pnm[pos] = '\0';
	strcat(pnm, fnm);
	if ( stat(pnm, &sbuf) == 0 ) {
		if ( S_ISDIR(sbuf.st_mode) )
			clear(pnm);
		else
			unlink(pnm);
	}
}
// UNICODE PROBLEM
void clear(const char *dir)
{
	char fnm[_MAX_PATH+1];
	DIR *ds;
	struct dirent *finfo;
	int dirnmlen;

	strcpy(fnm, dir);
	dirnmlen = strlen(fnm);
	if ( fnm[dirnmlen-1] != '/' ) {
		strcat(fnm, "/");
		dirnmlen++;
	}
	ds = opendir(dir);
	finfo = readdir(ds);
	while (finfo) {
		removeOne(fnm, dirnmlen, finfo->d_name);
		finfo = readdir(ds);
	}
	closedir(ds);
	rmdir(dir);
}
#endif

/*
 * If binaries were extracted, this should be called
 * to remove them
 */
void cleanUp(ARCHIVE_STATUS *status)
{
	if (status->temppath[0])
		clear(status->temppath);
}

/*
 * Helpers for embedders
 */
int getPyVersion(ARCHIVE_STATUS *status)
{
	return ntohl(status->cookie.pyvers);
}
void finalizePython(void)
{
	PI_Py_Finalize();
}
