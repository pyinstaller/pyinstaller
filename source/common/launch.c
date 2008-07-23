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
#ifdef WIN32
 #include <windows.h>
 #include <direct.h>
 #include <process.h>
 #include <io.h>
#else
 #include <unistd.h>
 #include <fcntl.h>
 #include <dlfcn.h>
 #include <dirent.h>
#endif
#include <sys/types.h>
#include <sys/stat.h>
#include "launch.h"
#ifndef NOZLIB
#include "zlib.h"
#endif

/*
 * Python Entry point declarations (see macros in launch.h).
 */
DECLVAR(Py_NoSiteFlag);
DECLVAR(Py_OptimizeFlag);
DECLVAR(Py_VerboseFlag);
DECLPROC(Py_Initialize);
DECLPROC(Py_Finalize);
DECLPROC(PyImport_ExecCodeModule);
DECLPROC(PyRun_SimpleString);
DECLPROC(Py_SetProgramName);
DECLPROC(PyImport_ImportModule);
DECLPROC(PyImport_AddModule);
DECLPROC(PyObject_SetAttrString);
DECLPROC(PyList_New);
DECLPROC(PyList_Append);
DECLPROC(Py_BuildValue);
DECLPROC(PyString_FromStringAndSize);
DECLPROC(PyObject_CallFunction);
DECLPROC(PyModule_GetDict);
DECLPROC(PyDict_GetItemString);
DECLPROC(PyErr_Clear);
DECLPROC(PyErr_Occurred);
DECLPROC(PyErr_Print);
DECLPROC(PySys_AddWarnOption);
DECLPROC(PyEval_InitThreads);
DECLPROC(PyEval_AcquireThread);
DECLPROC(PyEval_ReleaseThread);
DECLPROC(PyThreadState_Swap);
DECLPROC(Py_NewInterpreter);
DECLPROC(Py_EndInterpreter);
DECLPROC(PyInt_AsLong);
DECLPROC(PySys_SetObject);

#ifdef WIN32
#define PATHSEP ";"
#define SEP "/"
#else
#define PATHSEP ":"
#define SEP "/"
#endif

/* File Local Variables (all start with f_) */
static char f_archivename[_MAX_PATH+1];
static char f_homepath[_MAX_PATH+1];
static char f_temppath[_MAX_PATH+1] = { '\0' };
#ifdef WIN32
static char f_temppathraw[MAX_PATH+1];
static char f_homepathraw[_MAX_PATH+1];
#endif
static char *f_workpath = NULL;
static FILE *f_fp;
static int f_pkgstart;
static TOC *f_tocbuff = NULL;
static TOC *f_tocend = NULL;
static COOKIE f_cookie;

unsigned char *extract(TOC *ptoc);

/*
 * The functions in this file defined in reverse order so that forward 
 * declarations are not necessary.
 */


#ifndef _CONSOLE
/* This code will be used only on windows as for other platforms _CONSOLE
 * will be true. The code duplication in the functions below are because
 * standard macros with variable numer of arguments (variadic macros) are
 * supported by Microsoft only starting from Visual C++ 2005.
 */

#define MBTXTLEN 200

void mbfatalerror(const char *fmt, ...)
{
	char msg[MBTXTLEN];
	va_list args;

	va_start(args, fmt);
	_vsnprintf(msg, MBTXTLEN, fmt, args);
	msg[MBTXTLEN-1] = '\0';
	va_end(args);

	MessageBox(NULL, msg, "Fatal Error!", MB_OK | MB_ICONEXCLAMATION);
}

void mbothererror(const char *fmt, ...)
{
	char msg[MBTXTLEN];
	va_list args;

	va_start(args, fmt);
	_vsnprintf(msg, MBTXTLEN, fmt, args);
	msg[MBTXTLEN-1] = '\0';
	va_end(args);

	MessageBox(NULL, msg, "Error!", MB_OK | MB_ICONWARNING);
}

void mbvs(const char *fmt, ...)
{
	char msg[MBTXTLEN];
	va_list args;

	va_start(args, fmt);
	_vsnprintf(msg, MBTXTLEN, fmt, args);
	msg[MBTXTLEN-1] = '\0';
	va_end(args);

	MessageBox(NULL, msg, "Tracing", MB_OK);
}

#endif /* _CONSOLE */


#ifdef WIN32

int getTempPath(char *buff)
{
    int i;
    char *ret;
    char prefix[16];

    GetTempPath(MAX_PATH, buff);
    sprintf(prefix, "_MEI%d", getpid());

    // Windows does not have a race-free function to create a temporary
    // directory. Thus, we rely on _tempnam, and simply try several times
    // to avoid stupid race conditions.
    for (i=0;i<5;i++) {
        ret = _tempnam(buff, prefix);
        if (mkdir(ret) == 0) {
            strcpy(buff, ret);
            strcat(buff, "\\");
            free(ret);
            return 1;
        }
        free(ret);
    }
    return 0;
}

#else

int testTempPath(char *buff)
{
	strcat(buff, "/_MEIXXXXXX");
    if (mkdtemp(buff))
    {
        strcat(buff, "/");
        return 1;
    }
    return 0;   
}

int getTempPath(char *buff)
{
	static const char *envname[] = {
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

#endif

/*
 * Set up paths required by rest of this module
 * Sets f_archivename, f_homepath
 */
int setPaths(char const * archivePath, char const * archiveName)
{
#ifdef WIN32
	char *p;
#endif
	/* Get the archive Path */
	strcpy(f_archivename, archivePath);
	strcat(f_archivename, archiveName);

	/* Set homepath to where the archive is */
	strcpy(f_homepath, archivePath);
#ifdef WIN32
	strcpy(f_homepathraw, archivePath);
	for ( p = f_homepath; *p; p++ )
		if (*p == '\\')
			*p = '/';
#endif

	return 0;
}


/* 
 * Open the archive
 * Sets f_archiveFile, f_pkgstart, f_tocbuff and f_cookie.
 */
int openArchive()
{
	int filelen;

	/* Physically open the file */
	f_fp = fopen(f_archivename, "rb");
	if (f_fp == NULL) {
		VS("Cannot open archive: %s\n", f_archivename);
		return -1;
	}

	/* Seek to the Cookie at the end of the file. */
	fseek(f_fp, 0, SEEK_END);
	filelen = ftell(f_fp);
	if (fseek(f_fp, -(int)sizeof(COOKIE), SEEK_END)) 
	{
		VS("%s appears to be an invalid archive\n", f_archivename);
		return -1;
	}

	/* Read the Cookie, and check its MAGIC bytes */
	fread(&f_cookie, sizeof(COOKIE), 1, f_fp);
	if (strncmp(f_cookie.magic, MAGIC, strlen(MAGIC))) 
	{
		VS("%s has bad magic!\n", f_archivename);
		return -1;
	}

	/* From the cookie, calculate the archive start */
	f_pkgstart = filelen - ntohl(f_cookie.len);

	/* Read in in the table of contents */
	fseek(f_fp, f_pkgstart + ntohl(f_cookie.TOC), SEEK_SET);
	f_tocbuff = (TOC *) malloc(ntohl(f_cookie.TOClen));
	if (f_tocbuff == NULL) 
	{
		FATALERROR("Could not allocate buffer for TOC.");
		return -1;
	}
	fread(f_tocbuff, ntohl(f_cookie.TOClen), 1, f_fp);
	f_tocend = (TOC *) (((char *)f_tocbuff) + ntohl(f_cookie.TOClen));

	/* Check input file is still ok (should be). */
	if (ferror(f_fp))
	{
		FATALERROR("Error on file");
		return -1;
	}
	return 0;
}
#ifndef WIN32
#define HMODULE void *
#define HINSTANCE void *
#endif

int mapNames(HMODULE dll)
{
    /* Get all of the entry points that we are interested in */
	GETVAR(dll, Py_NoSiteFlag);
	GETVAR(dll, Py_OptimizeFlag);
	GETVAR(dll, Py_VerboseFlag);
	GETPROC(dll, Py_Initialize);
	GETPROC(dll, Py_Finalize);
	GETPROC(dll, PyImport_ExecCodeModule);
	GETPROC(dll, PyRun_SimpleString);
	GETPROC(dll, Py_SetProgramName);
	GETPROC(dll, PyImport_ImportModule);
	GETPROC(dll, PyImport_AddModule);
	GETPROC(dll, PyObject_SetAttrString);
	GETPROC(dll, PyList_New);
	GETPROC(dll, PyList_Append);
	GETPROC(dll, Py_BuildValue);
	GETPROC(dll, PyString_FromStringAndSize);
	GETPROC(dll, PyObject_CallFunction);
	GETPROC(dll, PyModule_GetDict);
	GETPROC(dll, PyDict_GetItemString);
	GETPROC(dll, PyErr_Clear);
	GETPROC(dll, PyErr_Occurred);
	GETPROC(dll, PyErr_Print);
	if (ntohl(f_cookie.pyvers) >= 21) {
		GETPROC(dll, PySys_AddWarnOption);
	}
	GETPROC(dll, PyEval_InitThreads);
	GETPROC(dll, PyEval_AcquireThread);
	GETPROC(dll, PyEval_ReleaseThread);
	GETPROC(dll, PyThreadState_Swap);
	GETPROC(dll, Py_NewInterpreter);
	GETPROC(dll, Py_EndInterpreter);
	GETPROC(dll, PyInt_AsLong);
	GETPROC(dll, PySys_SetObject);

	return 0;
}

/*
 * Load the Python DLL, and get all of the necessary entry points
 */
int loadPython()
{
	HINSTANCE dll;
	char dllpath[_MAX_PATH + 1];

#ifdef WIN32
	/* Determine the path */
	sprintf(dllpath, "%spython%02d.dll", f_homepathraw, ntohl(f_cookie.pyvers));

	/* Load the DLL */
	dll = LoadLibraryEx(dllpath, NULL, LOAD_WITH_ALTERED_SEARCH_PATH);  
	if (dll) {
		VS("%s\n", dllpath);
	}
	else {
		sprintf(dllpath, "%spython%02d.dll", f_temppathraw, ntohl(f_cookie.pyvers));
		dll = LoadLibraryEx(dllpath, NULL, LOAD_WITH_ALTERED_SEARCH_PATH );
		if (dll) {
			VS("%s\n", dllpath);
		}
	}
	if (dll == 0) {
		FATALERROR("Error loading Python DLL: %s (error code %d)\n",
			dllpath, GetLastError());
		return -1;
	}

	mapNames(dll);
#else

	/* Determine the path */
#ifdef __APPLE__
	sprintf(dllpath, "%sPython",
		f_workpath ? f_workpath : f_homepath);
#else
	sprintf(dllpath, "%slibpython%01d.%01d.so.1.0",
		f_workpath ? f_workpath : f_homepath,
		ntohl(f_cookie.pyvers) / 10, ntohl(f_cookie.pyvers) % 10);
#endif

	/* Load the DLL */
	dll = dlopen(dllpath, RTLD_NOW|RTLD_GLOBAL);
	if (dll) {
		VS("%s\n", dllpath);
	}
	if (dll == 0) {
		FATALERROR("Error loading Python lib '%s': %s\n",
			dllpath, dlerror());
		return -1;
	}

	mapNames(dll);

#endif

	return 0;
}

/*
 * use this from a dll instead of loadPython()
 * it will attach to an existing pythonXX.dll,
 * or load one if needed.
 */
int attachPython(int *loadedNew)
{
#ifdef WIN32
	HMODULE dll;
	char nm[_MAX_PATH + 1];

	/* Get python's name */
	sprintf(nm, "python%02d.dll", ntohl(f_cookie.pyvers));

	/* See if it's loaded */
	dll = GetModuleHandle(nm);  
	if (dll == 0) {
		*loadedNew = 1;
		return loadPython();
	}
	mapNames(dll);
	*loadedNew = 0;
#endif
	return 0;
}

/*
 * Return pointer to next toc entry.
 */
TOC *incrementTocPtr(TOC* ptoc)
{
	TOC *result = (TOC*)((char *)ptoc + ntohl(ptoc->structlen));
	if (result < f_tocbuff) {
		FATALERROR("Cannot read Table of Contents.\n");
		return f_tocend;
	}
	return result;
}
/*
 * external API for iterating TOCs
 */
TOC *getFirstTocEntry(void)
{
	return f_tocbuff;
}
TOC *getNextTocEntry(TOC *entry)
{
	TOC *rslt = (TOC*)((char *)entry + ntohl(entry->structlen));
	if (rslt >= f_tocend)
		return NULL;
	return rslt;
}
/*
 * A toc entry of type 'o' holds runtime options
 * toc->name is the arg
 * this is so you can freeze in command line args to Python
 */
int setRuntimeOptions(void)
{
	int unbuffered = 0;
	TOC *ptoc = f_tocbuff;
	while (ptoc < f_tocend) {
		if (ptoc->typcd == 'o') {
			VS("%s\n", ptoc->name);
			switch (ptoc->name[0]) {
			case 'v':
				*PI_Py_VerboseFlag = 1;
			break;
			case 'u':
				unbuffered = 1;
			break;
#ifdef HAVE_WARNINGS
			case 'W':
				if (ntohl(f_cookie.pyvers) >= 21) {
					PI_PySys_AddWarnOption(&ptoc->name[2]);
				}
			break;
#endif
			case 's':
				*PI_Py_NoSiteFlag = 0;
			break;
			case 'O':
				*PI_Py_OptimizeFlag = 1;
			break;
			}
		}
		ptoc = incrementTocPtr(ptoc);
	}
	if (unbuffered) {
#ifdef WIN32
		_setmode(fileno(stdin), O_BINARY);
		_setmode(fileno(stdout), O_BINARY);
#else
		fflush(stdout);
		fflush(stderr);
#ifdef HAVE_SETVBUF
		setvbuf(stdin, (char *)NULL, _IONBF, 0);
		setvbuf(stdout, (char *)NULL, _IONBF, 0);
		setvbuf(stderr, (char *)NULL, _IONBF, 0);
#else
		setbuf(stdin, (char *)NULL);
		setbuf(stdout, (char *)NULL);
		setbuf(stderr, (char *)NULL);
#endif
#endif
	}
	return 0;
}
/*
 * Start python - return 0 on success
 */
int startPython(int argc, char *argv[])
{
    /* Set PYTHONPATH so dynamic libs will load */
	static char pypath[2*_MAX_PATH + 14];
	int pathlen = 1;
	int i;
	char cmd[_MAX_PATH+1+80];
	char tmp[_MAX_PATH+1];
	PyObject *py_argv;
	PyObject *val;
	PyObject *sys;

	VS("Manipulating evironment\n");
	if (f_workpath && (strcmp(f_workpath, f_homepath) != 0)) {
		strcpy(pypath, "PYTHONPATH=");
		strcat(pypath, f_workpath);
		pypath[strlen(pypath)-1] = '\0';
		strcat(pypath, PATHSEP);
		strcat(pypath, f_homepath);
		pathlen = 2;
	}
	else {
		/* never extracted anything, or extracted to homepath - homepath will do */
		strcpy(pypath, "PYTHONPATH=");
		strcat(pypath, f_homepath);
	}
	/* don't chop off SEP if root directory */
#ifdef WIN32
	if (strlen(pypath) > 14)
#else
	if (strlen(pypath) > 12)
#endif
		pypath[strlen(pypath)-1] = '\0';

	putenv(pypath);
	VS("%s\n", pypath);
	/* Clear out PYTHONHOME to avoid clashing with any installation */
#ifdef WIN32
	putenv("PYTHONHOME=");
#endif

	/* Start python. */
	/* VS("Loading python\n"); */
	*PI_Py_NoSiteFlag = 1;	/* maybe changed to 0 by setRuntimeOptions() */
	setRuntimeOptions();
	PI_Py_SetProgramName(f_archivename); /*XXX*/
	PI_Py_Initialize();

	/* Set sys.path */
	/* VS("Manipulating Python's sys.path\n"); */
	strcpy(tmp, f_homepath);
	tmp[strlen(tmp)-1] = '\0';
	PI_PyRun_SimpleString("import sys\n");
	PI_PyRun_SimpleString("while sys.path:\n del sys.path[0]\n");
	sprintf(cmd, "sys.path.append('%s')", tmp);
	PI_PyRun_SimpleString (cmd);
	if (pathlen == 2) {
		strcpy(tmp, f_workpath);
		tmp[strlen(tmp)-1] = '\0';
		sprintf(cmd, "sys.path.insert(0, '%s')", tmp);
		PI_PyRun_SimpleString(cmd);
	}

	/* Set argv[0] to be the archiveName */
	py_argv = PI_PyList_New(0);
	val = PI_Py_BuildValue("s", f_archivename);
	PI_PyList_Append(py_argv, val);
	for (i = 1; i < argc; ++i) {
		val = PI_Py_BuildValue ("s", argv[i]);
		PI_PyList_Append (py_argv, val);
	}
	sys = PI_PyImport_ImportModule("sys");
	/* VS("Setting sys.argv\n"); */
	PI_PyObject_SetAttrString(sys, "argv", py_argv);

	/* Check for a python error */
	if (PI_PyErr_Occurred())
	{
		FATALERROR("Error detected starting Python VM.");
		return -1;
	}

	return 0;
}

/*
 * Import modules embedded in the archive - return 0 on success
 */
int importModules()
{
	PyObject *marshal;
	PyObject *marshaldict;
	PyObject *loadfunc;
	TOC *ptoc;
	PyObject *co;
	PyObject *mod;

	VS("importing modules from CArchive\n"); 

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
	ptoc = f_tocbuff;
	while (ptoc < f_tocend) {
		if (ptoc->typcd == 'm' || ptoc->typcd == 'M') 
		{
			unsigned char *modbuf = extract(ptoc);

			/* .pyc/.pyo files have 8 bytes header. Skip it and get a Python
			 * string directly pointing at the marshalled code.
			 */
			PyObject *mods = PI_PyString_FromStringAndSize(modbuf + 8,
				ntohl(ptoc->ulen) - 8);
            
			VS("%s\n", ptoc->name);
			
			co = PI_PyObject_CallFunction(loadfunc, "O", mods);
			mod = PI_PyImport_ExecCodeModule(ptoc->name, co);

			/* Check for errors in loading */
			if (mod == NULL) {
				FATALERROR("mod is NULL - %s", ptoc->name);
			}
			if (PI_PyErr_Occurred())
			{
				PI_PyErr_Print();
				PI_PyErr_Clear();
			}

			Py_DECREF(mods);
			free(modbuf);
		}
		ptoc = incrementTocPtr(ptoc); 
	}

	return 0;
}


/* Install a zlib from a toc entry
 * Return non zero on failure
 */
int installZlib(TOC *ptoc)
{
	int rc;
	int zlibpos = f_pkgstart + ntohl(ptoc->pos);
	char *tmpl = "sys.path.append(r\"%s?%d\")\n";
	char *cmd = (char *) malloc(strlen(tmpl) + strlen(f_archivename) + 32);
	sprintf(cmd, tmpl, f_archivename, zlibpos);
	/*VS(cmd);*/
	rc = PI_PyRun_SimpleString(cmd);
	if (rc != 0)
	{
		FATALERROR("Error in command: %s\n", cmd);
		free(cmd);
		return -1;
	}

	free(cmd);
	return 0;
}


/*
 * Install zlibs 
 * Return non zero on failure
 */
int installZlibs()
{
	TOC * ptoc;
	VS("Installing import hooks\n");

	/* Iterate through toc looking for zlibs (type 'z') */
	ptoc = f_tocbuff;
	while (ptoc < f_tocend) {
		if (ptoc->typcd == 'z') 
		{
			VS("%s\n", ptoc->name);
			installZlib(ptoc);
		}

		ptoc = incrementTocPtr(ptoc); 
	}
	return 0;
}

#ifndef NOZLIB
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
			OTHERERROR("Error %d from inflate: %s\n", rc,
					zstream.msg);
			return NULL;
		}
	}
	else {
		OTHERERROR("Error %d from inflateInit: %s\n", rc, zstream.msg);
		return NULL;
	}	

	return out;
}
#endif
/* 
 * extract an archive entry
 * returns pointer to the data (must be freed)
 */
unsigned char *extract(TOC *ptoc)
{
	unsigned char *data;
	unsigned char *tmp;

	fseek(f_fp, f_pkgstart + ntohl(ptoc->pos), SEEK_SET);
	data = (unsigned char *)malloc(ntohl(ptoc->len));
	if (data == NULL) {
		OTHERERROR("Could not allocate read buffer\n");
		return NULL;
	}
	fread(data, ntohl(ptoc->len), 1, f_fp);
	if (ptoc->cflag == '\1') {
#ifndef NOZLIB
		tmp = decompress(data, ptoc);
		free(data);
		data = tmp;
		if (data == NULL) {
			OTHERERROR("Error decompressing %s\n", ptoc->name);
			return NULL;
		}
#else
		FATALERROR("No ZLIB support but archive uses compression\n");
		return NULL;
#endif
	}
	return data;
}
/*
 * helper for extract2fs
 * which may try multiple places
 */
FILE *openTarget(char *path, char*name)
{
	struct stat sbuf;
	char fnm[_MAX_PATH+1];
	strcpy(fnm, path);
	strcat(fnm, name);
	if (stat(fnm, &sbuf) == 0) {
		OTHERERROR("WARNING: file already exists but should not: %s\n", fnm);
    }
	return fopen(fnm, "wb");
}
/*
 * extract from the archive
 * and copy to the filesystem 
 * relative to the directory the archive's in
 */
int extract2fs(TOC *ptoc)
{
#ifdef WIN32
	char *p;
#endif
	FILE *out;
	unsigned char *data = extract(ptoc);

	if (!f_workpath) {
		if (!getTempPath(f_temppath))
		{
            FATALERROR("INTERNAL ERROR: cannot create temporary directory!\n");
            return -1;
		}
#ifdef WIN32
		strcpy(f_temppathraw, f_temppath);
		for ( p=f_temppath; *p; p++ )
			if (*p == '\\')
				*p = '/';
#endif
		f_workpath = f_temppath;
	}
	
	out = openTarget(f_workpath, ptoc->name);

	if (out == NULL)  {
		FATALERROR("%s could not be extracted!\n", ptoc->name);
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
/*
 * extract all binaries (type 'b') to the filesystem
 */
int extractBinaries(char **workpath)
{
	TOC * ptoc = f_tocbuff;
	workpath[0] = '\0';
	VS("Extracting binaries\n");
	while (ptoc < f_tocend) {
		if (ptoc->typcd == 'b') 
		if (extract2fs(ptoc))
		return -1;
		ptoc = incrementTocPtr(ptoc); 
	}
	*workpath = f_workpath;
	return 0;
}
/* 
 * Run scripts
 * Return non zero on failure
 */
int runScripts()
{
	unsigned char *data;
	int rc = 0;
	TOC * ptoc = f_tocbuff;
	VS("Running scripts\n");

	/* Iterate through toc looking for scripts (type 's') */
	while (ptoc < f_tocend) {
		if (ptoc->typcd == 's') {
			/* Get data out of the archive.  */
			data = extract(ptoc);
			/* Run it */
			rc = PI_PyRun_SimpleString(data);
			/* log errors and abort */
			if (rc != 0) {
				VS("RC: %d from %s\n", rc, ptoc->name);
				return rc;
			}
			free(data);
		}

		ptoc = incrementTocPtr(ptoc); 
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
		VS("No __main__\n");
		goto done;
	}
	dict = PI_PyModule_GetDict(mod); /* NO ref added */
	if (!mod) {
		VS("No __dict__\n");
		goto done;
	}
	func = PI_PyDict_GetItemString(dict, name);
	if (func == NULL) { /* should explicitly check KeyError */
		VS("CallSimpleEntryPoint can't find the function name\n");
		rc = -2;
		goto done;
	}
	pyresult = PI_PyObject_CallFunction(func, "");
	if (pyresult==NULL) goto done;
	PI_PyErr_Clear();
	*presult = PI_PyInt_AsLong(pyresult);
	rc = PI_PyErr_Occurred() ? -1 : 0;
	VS( rc ? "Finished with failure\n" : "Finished OK\n");
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

/*
 * Launch an archive with the given fully-qualified path name
 * No command line, no extracting of binaries
 * Designed for embedding situations.
 */
int launchembedded(char const * archivePath, char  const * archiveName)
{
	char pathnm[_MAX_PATH];

	VS("START\n");
	strcpy(pathnm, archivePath);
	strcat(pathnm, archiveName);
	/* Set up paths */
	if (setPaths(archivePath, archiveName))
		return -1;
	VS("Got Paths\n");
	/* Open the archive */
	if (openArchive())
		return -1;
	VS("Opened Archive\n");
	/* Load Python DLL */
	if (loadPython())
		return -1;

	/* Start Python with silly command line */
	if (startPython(1, (char**)&pathnm))
		return -1;
	VS("Started Python\n");

	/* a signal to scripts */
	PI_PyRun_SimpleString("import sys;sys.frozen='dll'\n");
	VS("set sys.frozen\n");
	/* Import modules from archive - this is to bootstrap */
	if (importModules())
		return -1;
	VS("Imported Modules\n");
	/* Install zlibs - now import hooks are in place */
	if (installZlibs())
		return -1;
	VS("Installed Zlibs\n");
	/* Run scripts */
	if (runScripts())
		return -1;
	VS("All scripts run\n");
	if (PI_PyErr_Occurred()) {
		/*PyErr_Clear();*/
		VS("Some error occurred\n");
	}
	VS("OK.\n");

	return 0;
}

/* for finer grained control */
/*
 * initialize (this always needs to be done)
 */
int init(char const * archivePath, char  const * archiveName, char const * workpath)
{
#ifdef WIN32
	char *p;
#endif

	if (workpath) {
		f_workpath = (char *)workpath;
#ifdef WIN32
		strcpy(f_temppathraw, f_workpath);
		for ( p = f_temppathraw; *p; p++ )
			if (*p == '/')
				*p = '\\';
#endif
	}

	/* Set up paths */
	if (setPaths(archivePath, archiveName))
		return -1;

	/* Open the archive */
	if (openArchive())
		return -1;

	return 0;
}
/* once init'ed, you might want to extractBinaries()
 * If you do, what comes after is very platform specific.
 * Once you've taken care of the platform specific details,
 * or if there are no binaries to extract, you go on
 * to doIt(), which is the important part
 */
int doIt(int argc, char *argv[]) 
{
	int rc = 0;
	/* Load Python DLL */
	if (loadPython())
		return -1;

	/* Start Python. */
	if (startPython(argc, argv))
		return -1;

	/* Import modules from archive - bootstrap */
	if (importModules())
		return -1;

	/* Install zlibs  - now all hooks in place */
	if (installZlibs())
		return -1;

	/* Run scripts */
	rc = runScripts();

	VS("OK.\n");

	return rc;
}
void clear(const char *dir);
#ifdef WIN32
void removeOne(char *fnm, int pos, struct _finddata_t finfo)
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
void clear(const char *dir) 
{
	char fnm[_MAX_PATH+1];
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
		removeOne(fnm, dirnmlen, finfo);
		while ( _findnext(h, &finfo) == 0 ) 
			removeOne(fnm, dirnmlen, finfo);
		_findclose(h);
	}
	rmdir(dir);
}
#else
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
void cleanUp()
{
	if (f_temppath[0])
		clear(f_temppath);
}
/*
 * Helpers for embedders
 */
int getPyVersion(void)
{
	return ntohl(f_cookie.pyvers);
}
void finalizePython(void)
{
	PI_Py_Finalize();
}

