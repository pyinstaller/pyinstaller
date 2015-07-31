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
    #include <windows.h>  // HMODULE
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

    // Are we going to load the Python 2.x library?
    is_py2 = (pyvers / 10) == 2;

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

    sprintf(dllname,
            "libpython%01d.%01d.a(libpython%01d.%01d.so)",
            pyvers_major, pyvers_minor, pyvers_major, pyvers_minor);
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
			  if (is_py2) {
			    PI_Py2Sys_AddWarnOption(&ptoc->name[2]);
			  } else {
			    mbstowcs(wchar_tmp, &ptoc->name[2], PATH_MAX);
			    PI_PySys_AddWarnOption(wchar_tmp);
			  };
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
    /* last parameter '0' means do not update sys.path. */
    if (is_py2) {
      // For Python2, status->argv must be "char **". In Python 2.7's
      // `main.c`, argv is used without any other handling, so do we.
      PI_Py2Sys_SetArgvEx(status->argc, status->argv_char, 0);
    } else {
      PI_PySys_SetArgvEx(status->argc, status->argv, 0);
    };
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
	static char pypath[2*PATH_MAX + 14]; /* Statics are zero-initialized */
	int i;
    /* Temporary buffer for conversion of string to wide string. */
	wchar_t wchar_tmp_pypath[PATH_MAX+1];
	wchar_t wchar_tmp_pyhome[PATH_MAX+1];

    if (is_py2) {
      PI_Py2_SetProgramName(status->archivename);
      // TODO is this all, PyInstaller 2.1 did here?
    } else {
      // TODO archivename is not mbs - #1323
      mbstowcs(_program_name, status->archivename, PATH_MAX);
      // In Python 3 Py_SetProgramName() should be called before Py_SetPath().
      PI_Py_SetProgramName(_program_name);
    };

    /* Set the PYTHONPATH
     * On Python 3, we must set PYTHONPATH to have base_library.zip before
     * calling Py_Initialize as it needs the codecs and other modules.
     * mainpath must be last because _pyi_bootstrap uses sys.path[-1] as SYS_PREFIX
     */
    VS("LOADER: Manipulating environment (PYTHONPATH, PYTHONHOME)\n");
    strncat(pypath, status->mainpath, strlen(status->mainpath));
    if (!is_py2) {
      /* Append /base_library.zip to existing mainpath and then add actual mainpath */
      strncat(pypath, PYI_SEPSTR, strlen(PYI_SEPSTR));
      strncat(pypath, "base_library.zip", strlen("base_library.zip"));
      strncat(pypath, PYI_PATHSEPSTR, strlen(PYI_PATHSEPSTR));
      strncat(pypath, status->mainpath, strlen(status->mainpath));
    };

    VS("LOADER: Pre-init PYTHONPATH is %s\n", pypath);
    if (is_py2) {
      pyi_setenv("PYTHONPATH", pypath);
    } else {
      // TODO: is pypath mbs? probably not.
      mbstowcs(wchar_tmp_pypath, pypath, PATH_MAX);
      PI_Py_SetPath(wchar_tmp_pypath);
    };

    /* Set PYTHONHOME by using function from Python C API. */
    strcpy(pypath, status->mainpath);
    if (is_py2) {
      VS("LOADER: PYTHONHOME is %s\n", pypath);
      PI_Py2_SetPythonHome(pypath);
    } else {
      mbstowcs(wchar_tmp_pyhome, pypath, PATH_MAX);
      VS("LOADER: PYTHONHOME is %S\n", wchar_tmp_pyhome);
      PI_Py_SetPythonHome(wchar_tmp_pyhome);
    };

    /* Start python. */
    VS("LOADER: Setting runtime options\n");
    pyi_pylib_set_runtime_opts(status);

	/*
	 * Py_Initialize() may rudely call abort(), and on Windows this triggers the error
	 * reporting service, which results in a dialog box that says "Close program", "Check
	 * for a solution", and also "Debug" if Visual Studio is installed. The dialog box
	 * makes it frustrating to run the test suite.
	 *
	 * For debug builds of the bootloader, disable the error reporting before calling
	 * Py_Initialize and enable it afterward.
	 */

#if defined(_WIN32) && defined(LAUNCH_DEBUG)
	SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX);
#endif

	VS("LOADER: Initializing python\n");
	PI_Py_Initialize();

#if defined(_WIN32) && defined(LAUNCH_DEBUG)
	SetErrorMode(0);
#endif

	/*
	 * Set sys.path list.
	 * Python's default sys.path is no good - it includes the working directory
	 * and the folder containing the executable. Replace sys.path with only
	 * the paths we want.
	 */
	VS("LOADER: Overriding Python's sys.path\n");
	VS("LOADER: Post-init PYTHONPATH is %s\n", pypath);
	if (is_py2) {
	   PI_Py2Sys_SetPath(pypath);
	} else {
	   PI_PySys_SetPath(wchar_tmp_pypath);
	};

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
			if (is_py2) {
			  co = PI_PyObject_CallFunction(loadfunc, "s#", modbuf+8, ntohl(ptoc->ulen)-8);
			} else {
			  // It looks like from python 3.3 the header
			  // size was changed to 12 bytes.
			  co = PI_PyObject_CallFunction(loadfunc, "y#", modbuf+12, ntohl(ptoc->ulen)-12);
			};
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
 * The installation is done by adding an entry like
 *    absolute_path/dist/hello_world/hello_world?123456
 * to sys.path. The end number is the offset where the
 * Python bootstrap code should read the zip data.
 * Return non zero on failure.
 * NB: This entry is removed from sys.path duringby the bootstrap scripts.
 */
int pyi_pylib_install_zlib(ARCHIVE_STATUS *status, TOC *ptoc)
{
	int rc;
	int zlibpos = status->pkgstart + ntohl(ptoc->pos);
	// TODO Is there a better way to avoid call python code? Probably any API call?
	char *tmpl = "import sys; sys.path.append(r\"%s?%d\")\n";
	// +32 for the number, +2 as cushion
	char cmd[2*PATH_MAX + 32 + 2];
	sprintf(cmd, tmpl, status->archivename, zlibpos);
	VS("LOADER: %s", cmd);
	rc = PI_PyRun_SimpleString(cmd);
	if (rc != 0)
	{
		FATALERROR("Error in command: %s\n", cmd);
		return -1;
	}

	return 0;
}


/*
 * Install PYZ
 * Return non zero on failure
 */
int pyi_pylib_install_zlibs(ARCHIVE_STATUS *status)
{
	TOC * ptoc;
	VS("LOADER: Installing PYZ archive with Python modules.\n");

	/* Iterate through toc looking for zlibs (PYZ, type 'z') */
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
