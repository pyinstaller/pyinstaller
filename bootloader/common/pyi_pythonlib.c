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
 * Functions to load, initialize and launch Python.
 */


#ifdef WIN32
    #include <windows.h>
    #include <fcntl.h>  // O_BINARY
    #include <io.h>  // _setmode
    #include <winsock.h>  // ntohl
#else
    #include <limits.h>  // PATH_MAX
    #include <netinet/in.h>  // ntohl
#endif
#include <stddef.h>  // ptrdiff_t
#include <stdio.h>
#include <string.h>


/* PyInstaller headers. */
#include "stb.h"
#include "pyi_global.h"
#include "pyi_archive.h"
#include "pyi_utils.h"
#include "pyi_python.h"


/*
 * Load the Python DLL, and get all of the necessary entry points
 */
int pyi_pylib_load(ARCHIVE_STATUS *status)
{
	dylib_t dll;
	char dllpath[PATH_MAX];
    char dllname[64];
    int pyvers = ntohl(status->cookie.pyvers);

/*
 * On AIX Append the shared object member to the library path
 * to make it look like this:
 *   libpython2.6.a(libpython2.6.so)
 */
#ifdef AIX
    /*
     * On AIX 'ar' archives are used for both static and shared object.
     * To load a shared object from a library, it should be loaded like this:
     *   dlopen("libpython2.6.a(libpython2.6.so)", RTLD_MEMBER)
     */
    uint32_t pyvers_major;
    uint32_t pyvers_minor;

    pyvers_major = pyvers / 10;
    pyvers_minor = pyvers % 10;

    sprintf(dllname, "(libpython%01d.%01d.so)", pyvers_major, pyvers_minor);
#else
    strcpy(dllname, status->cookie.pylibname);
#endif

    /*
     * Look for Python library in homepath or temppath.
     * It depends on the value of mainpath.
     */
    pyi_path_join(dllpath, status->mainpath, dllname);


    VS("LOADER: Python library: %s\n", dllpath);

	/* Load the DLL */
    dll = pyi_utils_dlopen(dllpath);

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

	pyi_python_map_names(dll, pyvers);
	return 0;
}

/*
 * Use this from a dll instead of pyi_pylib_load().
 * It will attach to an existing pythonXX.dll or load one if needed.
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
	pyi_python_map_names(dll, pyvers);
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
			VS("LOADER: %s\n", ptoc->name);
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
		ptoc = pyi_arch_increment_toc_ptr(status, ptoc);
	}
	if (unbuffered) {
#ifdef WIN32
		_setmode(fileno(stdin), _O_BINARY);
		_setmode(fileno(stdout), _O_BINARY);
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

    // TODO set pythonpath by function from Python C API (Python 2.6+)
    /* Set the PYTHONPATH */
	VS("LOADER: Manipulating evironment\n");
    strcpy(pypath, status->mainpath);
	VS("LOADER: PYTHONPATH=%s\n", pypath);
	pyi_setenv("PYTHONPATH", pypath);

	/* Clear out PYTHONHOME to avoid clashing with any Python installation. */
	pyi_unsetenv("PYTHONHOME");

    /* Set PYTHONHOME by using function from Python C API. */
    strcpy(pypath, status->mainpath);
	VS("LOADER: PYTHONHOME=%s\n", pypath);
    PI_Py_SetPythonHome(pypath);


	/* Start python. */
	/* VS("Loading python\n"); */
	*PI_Py_NoSiteFlag = 1;	/* maybe changed to 0 by pyi_pylib_set_runtime_opts() */
    *PI_Py_FrozenFlag = 1;
    pyi_pylib_set_runtime_opts(status);
	PI_Py_SetProgramName(status->archivename); /*XXX*/
	PI_Py_Initialize();

    // TODO set sys.path by function from Python C API (Python 2.6+)
	/* Set sys.path */
	VS("LOADER: Manipulating Python's sys.path\n");
	PI_PyRun_SimpleString("import sys\n");
	PI_PyRun_SimpleString("del sys.path[:]\n");
    if (status->temppath[0] != PYI_NULLCHAR) {
        strcpy(tmp, status->temppath);
	    sprintf(cmd, "sys.path.append(r\"%s\")", tmp);
        PI_PyRun_SimpleString(cmd);
    }

	strcpy(tmp, status->homepath);
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

	VS("LOADER: importing modules from CArchive\n");

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
			unsigned char *modbuf = pyi_arch_extract(status, ptoc);

			VS("LOADER: extracted %s\n", ptoc->name);

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
		ptoc = pyi_arch_increment_toc_ptr(status, ptoc);
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
	VS("LOADER: Installing import hooks\n");

	/* Iterate through toc looking for zlibs (type 'z') */
	ptoc = status->tocbuff;
	while (ptoc < status->tocend) {
		if (ptoc->typcd == ARCHIVE_ITEM_PYZ)
		{
			VS("LOADER: %s\n", ptoc->name);
			pyi_pylib_install_zlib(status, ptoc);
		}

		ptoc = pyi_arch_increment_toc_ptr(status, ptoc);
	}
	return 0;
}

void pyi_pylib_finalize(ARCHIVE_STATUS *status)
{
    /*
     * Call this function only if Python library was initialized.
     *
     * Otherwise it should be NULL pointer. If Python library is not properly
     * loaded then calling this function might cause some segmentation faults.
     */
    if (status->is_pylib_loaded == true) {
        VS("LOADER: Cleaning up Python interpreter.\n");
        PI_Py_Finalize();
    }
}
