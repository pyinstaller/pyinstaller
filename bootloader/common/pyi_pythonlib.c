/*
 * Functions to load, initialize and launch Python.
 *
 * Copyright (C) 2012, Martin Zibricky
 * Copyright (C) 2005-2011, Giovanni Bajo
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


// TODO leave only necessary header includes.
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
 #include <stdarg.h>
#endif
#include <sys/types.h>
#include <sys/stat.h>
#include "launch.h"
#include <string.h>
#include "zlib.h"

#include "pyi_global.h"
#include "pyi_python.h"
#include "pyi_utils.h"
#include "pyi_archive.h"
#include "pyi_pythonlib.h"


/*
 * Python Entry point declarations (see macros in pyi_python.h).
 */
DECLVAR(Py_FrozenFlag);
DECLVAR(Py_NoSiteFlag);
DECLVAR(Py_OptimizeFlag);
DECLVAR(Py_VerboseFlag);
DECLPROC(Py_Initialize);
DECLPROC(Py_Finalize);
DECLPROC(Py_IncRef);
DECLPROC(Py_DecRef);
DECLPROC(Py_SetPythonHome);
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
    GETPROC(dll, Py_SetPythonHome);
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

    return 0;
}


/*
 * Set up paths required by rest of this module
 * Sets f_archivename, f_homepath
 */
int pyi_arch_set_paths(ARCHIVE_STATUS *status, char const * archivePath, char const * archiveName)
{
#ifdef WIN32
	char *p;
#endif
	/* Get the archive Path */
	strcpy(status->archivename, archivePath);
	strcat(status->archivename, archiveName);

	/* Set homepath to where the archive is */
	strcpy(status->homepath, archivePath);
#ifdef WIN32
    /* Replace backslashes with forward slashes. */
    // TODO eliminate the need for this conversion and homepathraw and temppathraw
	strcpy(status->homepathraw, archivePath);
	for ( p = status->homepath; *p; p++ )
		if (*p == '\\')
			*p = '/';
#endif

    /*
     * Initial value of mainpath is homepath. It might be overriden
     * by temppath if it is available.
     */
    status->has_temp_directory = false;
#ifdef WIN32
	strcpy(status->mainpath, status->homepathraw);
#else
	strcpy(status->mainpath, status->homepath);
#endif

	return 0;
}


/*
 * Load the Python DLL, and get all of the necessary entry points
 */
int pyi_pylib_load(ARCHIVE_STATUS *status)
{
	dylib_t dll;
	char dllpath[PATH_MAX + 1];
    char dllname[64];
    int pyvers = ntohl(status->cookie.pyvers);

#ifdef AIX
    /*
     * On AIX 'ar' archives are used for both static and shared object.
     * To load a shared object from a library, it should be loaded like this:
     *   dlopen("libpython2.6.a(libpython2.6.so)", RTLD_MEMBER)
     */
    uint32_t pyvers_major;
    uint32_t pyvers_minor;
#endif

    strcpy(dllname, status->cookie.pylibname);

    /*
     * Look for Python library in homepath or temppath.
     * It depends on the value of mainpath.
     */
    strcpy(dllpath, status->mainpath);

#ifdef AIX
    pyvers_major = pyvers / 10;
    pyvers_minor = pyvers % 10;

    /* Append the shared object member to the library path
     * to make it look like this:
     *   libpython2.6.a(libpython2.6.so)
     */
    sprintf(dllpath + strlen(dllpath), "(libpython%01d.%01d.so)", pyvers_major, pyvers_minor);
#endif

    /* Append Python library name to dllpath. */
    strcat(dllpath, dllname);
    VS("Python library: %s\n", dllpath);

	/* Load the DLL */
    dll = pyi_dlopen(dllpath);

    /* Check success of loading Python library. */
	if (dll == 0) {
#ifdef WIN32
		FATALERROR("Error loading Python DLL: %s (error code %d)\n",
			dllpath, GetLastError());
#else
		FATALERROR("Error loading Python lib '%s': %s\n",
			dllpath, dlerror());
#endif
		return -1;
	}

	mapNames(dll, pyvers);
	return 0;
}

/*
 * use this from a dll instead of pyi_pylib_load()
 * it will attach to an existing pythonXX.dll,
 * or load one if needed.
 */
int pyi_pylib_attach(ARCHIVE_STATUS *status, int *loadedNew)
{
#ifdef WIN32
	HMODULE dll;
	char nm[PATH_MAX + 1];
    int pyvers = ntohl(status->cookie.pyvers);

	/* Get python's name */
	sprintf(nm, "python%02d.dll", pyvers);

	/* See if it's loaded */
	dll = GetModuleHandleA(nm);
	if (dll == 0) {
		*loadedNew = 1;
		return pyi_pylib_load(status);
	}
	mapNames(dll, pyvers);
	*loadedNew = 0;
#endif
	return 0;
}

/*
 * A toc entry of type 'o' holds runtime options
 * toc->name is the arg
 * this is so you can freeze in command line args to Python
 */
static int pyi_pylib_set_runtime_opts(ARCHIVE_STATUS *status)
{
	int unbuffered = 0;
	TOC *ptoc = status->tocbuff;
	while (ptoc < status->tocend) {
		if (ptoc->typcd == ARCHIVE_ITEM_RUNTIME_OPTION) {
			VS("%s\n", ptoc->name);
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

/*
 * Start python - return 0 on success
 */
int pyi_pylib_start_python(ARCHIVE_STATUS *status, int argc, char *argv[])
{
    /* Set PYTHONPATH so dynamic libs will load.
     * PYTHONHOME for function Py_SetPythonHome() should point
     * to a zero-terminated character string in static storage. */
	static char pypath[2*PATH_MAX + 14];
	int pathlen = 1;
	int i;
	char cmd[PATH_MAX+1+80];
	char tmp[PATH_MAX+1];
	PyObject *py_argv;
	PyObject *val;
	PyObject *sys;

    /* Set the PYTHONPATH */
	VS("Manipulating evironment\n");
    strcpy(pypath, status->mainpath);
	/* don't chop off SEP if root directory */
#ifdef WIN32
	if (strlen(pypath) > 14)
#else
	if (strlen(pypath) > 12)
#endif
		pypath[strlen(pypath)-1] = '\0';

	pyi_setenv("PYTHONPATH", pypath);
	VS("PYTHONPATH=%s\n", pypath);


	/* Clear out PYTHONHOME to avoid clashing with any Python installation. */
	pyi_unsetenv("PYTHONHOME");

    /* Set PYTHONHOME by using function from Python C API. */
    strcpy(pypath, status->mainpath);
    /* On Windows remove back slash '\\' from the end. */
    // TODO remove this hook when path handling is fixed in bootloader.
    #ifdef WIN32
    /* Remove trailing slash in directory path. */
    pypath[strlen(pypath)-1] = '\0';
    #endif
    PI_Py_SetPythonHome(pypath);
	VS("PYTHONHOME=%s\n", pypath);


	/* Start python. */
	/* VS("Loading python\n"); */
	*PI_Py_NoSiteFlag = 1;	/* maybe changed to 0 by pyi_pylib_set_runtime_opts() */
    *PI_Py_FrozenFlag = 1;
    pyi_pylib_set_runtime_opts(status);
	PI_Py_SetProgramName(status->archivename); /*XXX*/
	PI_Py_Initialize();

	/* Set sys.path */
	/* VS("Manipulating Python's sys.path\n"); */
	PI_PyRun_SimpleString("import sys\n");
	PI_PyRun_SimpleString("del sys.path[:]\n");
    if (status->temppath[0] != '\0') {
        strcpy(tmp, status->temppath);
	    tmp[strlen(tmp)-1] = '\0';
	    sprintf(cmd, "sys.path.append(r\"%s\")", tmp);
        PI_PyRun_SimpleString(cmd);
    }

	strcpy(tmp, status->homepath);
	tmp[strlen(tmp)-1] = '\0';
	sprintf(cmd, "sys.path.append(r\"%s\")", tmp);
	PI_PyRun_SimpleString (cmd);

	/* Set argv[0] to be the archiveName */
	py_argv = PI_PyList_New(0);
	val = PI_Py_BuildValue("s", status->archivename);
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
int pyi_pylib_import_modules(ARCHIVE_STATUS *status)
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
	ptoc = status->tocbuff;
	while (ptoc < status->tocend) {
		if (ptoc->typcd == ARCHIVE_ITEM_PYMODULE || ptoc->typcd == ARCHIVE_ITEM_PYPACKAGE)
		{
			unsigned char *modbuf = extract(status, ptoc);

			VS("extracted %s\n", ptoc->name);

			/* .pyc/.pyo files have 8 bytes header. Skip it and load marshalled
			 * data form the right point.
			 */
			co = PI_PyObject_CallFunction(loadfunc, "s#", modbuf+8, ntohl(ptoc->ulen)-8);
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

			free(modbuf);
		}
		ptoc = incrementTocPtr(status, ptoc);
	}

	return 0;
}


/* Install a zlib from a toc entry
 * Return non zero on failure
 */
int pyi_pylib_install_zlib(ARCHIVE_STATUS *status, TOC *ptoc)
{
	int rc;
	int zlibpos = status->pkgstart + ntohl(ptoc->pos);
	char *tmpl = "sys.path.append(r\"%s?%d\")\n";
	char *cmd = (char *) malloc(strlen(tmpl) + strlen(status->archivename) + 32);
	sprintf(cmd, tmpl, status->archivename, zlibpos);
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
int pyi_pylib_install_zlibs(ARCHIVE_STATUS *status)
{
	TOC * ptoc;
	VS("Installing import hooks\n");

	/* Iterate through toc looking for zlibs (type 'z') */
	ptoc = status->tocbuff;
	while (ptoc < status->tocend) {
		if (ptoc->typcd == ARCHIVE_ITEM_PYZ)
		{
			VS("%s\n", ptoc->name);
			pyi_pylib_install_zlib(status, ptoc);
		}

		ptoc = incrementTocPtr(status, ptoc);
	}
	return 0;
}

void pyi_pylib_finalize(void)
{
	PI_Py_Finalize();
}


