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


#ifdef _WIN32
    #include <windows.h>
    #include <fcntl.h>  // O_BINARY
    #include <io.h>  // _setmode
    #include <winsock.h>  // ntohl
#else
    #include <dlfcn.h>  // dlerror
    #include <limits.h>  // PATH_MAX
    #include <netinet/in.h>  // ntohl
    #include <locale.h>  // setlocale
    #include <stdlib.h>  // mbstowcs
#endif
#include <stddef.h>  // ptrdiff_t
#include <stdio.h>
#include <string.h>


/* PyInstaller headers. */
#include "pyi_global.h"
#include "pyi_path.h"
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
#ifdef _WIN32
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
#ifdef _WIN32
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
	wchar_t wchar_tmp[PATH_MAX+1];

	/*
     * Startup flags - default values. 1 means enabled, 0 disabled.
     */
     /* Suppress 'import site'. */
	*PI_Py_NoSiteFlag = 1;
	/* Needed by getpath.c from Python. */
    *PI_Py_FrozenFlag = 1;
    /* Suppress writing bytecode files (*.py[co]) */
    *PI_Py_DontWriteBytecodeFlag = 1;
    /* Do not try to find any packages in user's site directory. */
    *PI_Py_NoUserSiteDirectory = 1;
    /* This flag ensures PYTHONPATH and PYTHONHOME are ignored by Python. */
    *PI_Py_IgnoreEnvironmentFlag = 1;
    /* Disalbe verbose imports by default. */
    *PI_Py_VerboseFlag = 0;

    /* Override some runtime options by custom values from PKG archive.
     * User is allowed to changes these options. */
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
			    // TODO Python 2 uses 'char' here.
                mbstowcs(wchar_tmp, &ptoc->name[2], PATH_MAX);
                PI_PySys_AddWarnOption(wchar_tmp);
			break;
			case 'O':
				*PI_Py_OptimizeFlag = 1;
			break;
			}
		}
		ptoc = pyi_arch_increment_toc_ptr(status, ptoc);
	}
	if (unbuffered) {
#ifdef _WIN32
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
 * Set Python list sys.argv from *argv/argc. (Command-line options).
 * sys.argv[0] should be full absolute path to the executable (Derived from
 * status->archivename).
 */
static void pyi_pylib_set_sys_argv(ARCHIVE_STATUS *status)
{
	VS("LOADER: Setting sys.argv\n");
    /*
    TODO Python2 find workaround how to set sys.path
    - convert argv[x] to Py_UNICODE strings - PyUnicode_FromWideChar(const wchar_t *w, Py_ssize_t size)
    - create Python string and set this string to sys.path - use Python C api.
    */
    /* '0' means do not update sys.path. */
    PI_PySys_SetArgvEx(status->argc, status->argv, 0);
}

/* Required for Py_SetProgramName */
wchar_t _program_name[PATH_MAX+1];
	
/*
 * Start python - return 0 on success
 */
int pyi_pylib_start_python(ARCHIVE_STATUS *status)
{
    /* Set PYTHONPATH so dynamic libs will load.
     * PYTHONHOME for function Py_SetPythonHome() should point
     * to a zero-terminated character string in static storage. */
	static char pypath[2*PATH_MAX + 14];
	int pathlen = 1;
	int i;
	char cmd[PATH_MAX+1+80];
	char tmp[PATH_MAX+1];
    /* Temporary buffer for conversion of string to wide string. */
	wchar_t wchar_tmp[PATH_MAX+1];
	wchar_t wchar_tmp2[PATH_MAX+1];
	PyObject *py_argv;
	PyObject *val;
	PyObject *sys;

	wchar_t *aabbcc;

    /* In Python 3 Py_SetProgramName() should be called before Py_SetPath(). */
    // TODO Fix this wchar_t/char thing to work in Python 3 and Python 2 (Py3 requires wchar_t type)
    mbstowcs(_program_name, status->archivename, PATH_MAX);
    //PI_Py_SetProgramName(status->archivename);
    PI_Py_SetProgramName(_program_name);

    // TODO set pythonpath by function from Python C API (Python 2.6+)
    /* Set the PYTHONPATH */
	VS("LOADER: Manipulating evironment (PYTHONPATH, PYTHONHOME)\n");
	// TODO Check if base_library.zip should be first in sys.path.
    /* Append base_library.zip to PYTHONPATH - necessary for Py_Initialize() in Python 3. */
    // TODO Check if base_library.zip does not hurt for Python 2. */
    strncat(pypath, status->mainpath, strlen(status->mainpath));
    strncat(pypath, PYI_SEPSTR, strlen(PYI_SEPSTR));
    strncat(pypath, "base_library.zip", strlen("base_library.zip"));
    /* Append status->mainpath to PYTHONPATH. */
    strncat(pypath, PYI_PATHSEPSTR, strlen(PYI_PATHSEPSTR));
    strncat(pypath, status->mainpath, strlen(status->mainpath));
    // TODO check if status->homepath should be in PYTHONPATH in onefile mode.
    /*if (status->temppath[0] != PYI_NULLCHAR) {
        strcat(pypath, PYI_PATHSEPSTR);
        strcpy(pypath, status->homepat);
    }*/
	VS("LOADER: PYTHONPATH is %s\n", pypath);
    // TODO Fix this wchar_t/char thing to work in Python 3 and Python 2 (Py3 requires wchar_t type)
    mbstowcs(wchar_tmp, pypath, PATH_MAX);
    // TODO Skip this function for Python2.
    PI_Py_SetPath(wchar_tmp);

    /* Set PYTHONHOME by using function from Python C API. */
    strcpy(pypath, status->mainpath);
    // TODO Fix this wchar_t/char thing to work in Python 3 and Python 2 (Py3 requires wchar_t type)
	//VS("LOADER: PYTHONHOME is %s\n", pypath);
    mbstowcs(wchar_tmp2, pypath, PATH_MAX);
	VS("LOADER: PYTHONHOME is %S\n", wchar_tmp2);
    //PI_Py_SetPythonHome(pypath);
    PI_Py_SetPythonHome(wchar_tmp2);

	/* Start python. */

	VS("LOADER: Setting runtime options\n");

   pyi_pylib_set_runtime_opts(status);

	VS("LOADER: Initializing python\n");
	PI_Py_Initialize();

	/*
	 * Set sys.path list. In Python 2 this is the only way to set sys.path.
	 * Without
	 * Python 3 requires something on sys.path before calling Py_Initialize.
	 */
	// TODO try out if setting sys.path really works in Python 2 with this function.
	// TODO use directly wchar_t - no char.
	PI_PySys_SetPath(wchar_tmp);

    /* Setting sys.argv should be after Py_Initialize() call. */
    pyi_pylib_set_sys_argv(status);

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
            // TODO It looks like from python 3.3 the header size was changed to 12 bytes. We might want to put here python version check to make the bootloader working again with previous versions.
            // co = PI_PyObject_CallFunction(loadfunc, "s#", modbuf+8, ntohl(ptoc->ulen)-8);
			co = PI_PyObject_CallFunction(loadfunc, "y#", modbuf+12, ntohl(ptoc->ulen)-12);
			if (co != NULL) {
				VS("LOADER: callfunction returned...\n");
				mod = PI_PyImport_ExecCodeModule(ptoc->name, co);
			} else {
                // TODO callfunctions might return NULL - find yout why and foor what modules.
				VS("LOADER: callfunction returned NULL");
				mod = NULL;
			}

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


/*
 * Install a zlib from a toc entry.
 *
 * The installation is done by adding  file like
 *    absolute_path/dist/hello_world/hello_world?123456
 * to sys.path. The end number is the offset where the
 * Python bootstrap code should read the zip data.
 * Return non zero on failure
 */
int pyi_pylib_install_zlib(ARCHIVE_STATUS *status, TOC *ptoc)
{
	int rc;
	int zlibpos = status->pkgstart + ntohl(ptoc->pos);
	// TODO Is there a better way to avoid call python code? Probably any API call?
	char *tmpl = "import sys; sys.path.append(r\"%s?%d\")\n";
	char *cmd = (char *) malloc(strlen(tmpl) + strlen(status->archivename) + 32);
	sprintf(cmd, tmpl, status->archivename, zlibpos);
	VS("LOADER: %s\n", cmd);
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
