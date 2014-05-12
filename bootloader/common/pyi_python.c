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
 * Python.h replacements.
 */


#ifdef _WIN32
    #include <windows.h>
    #include <winsock.h>  // ntohl
#else
    #include <dlfcn.h>  // dlsym
#endif
#include <stddef.h>  // ptrdiff_t
#include <stdlib.h>


/* PyInstaller headers. */
#include "pyi_global.h"
#include "pyi_python.h"


/*
 * Python Entry point declarations (see macros in pyi_python.h).
 */
DECLVAR(Py_FrozenFlag);
DECLVAR(Py_NoSiteFlag);
DECLVAR(Py_OptimizeFlag);
DECLVAR(Py_VerboseFlag);
DECLVAR(Py_IgnoreEnvironmentFlag);
DECLVAR(Py_DontWriteBytecodeFlag);
DECLVAR(Py_NoUserSiteDirectory);

DECLPROC(Py_Initialize);
DECLPROC(Py_Finalize);
DECLPROC(Py_IncRef);
DECLPROC(Py_DecRef);
DECLPROC(Py_SetPath);
DECLPROC(Py_SetPythonHome);
DECLPROC(PyImport_ExecCodeModule);
DECLPROC(PyRun_SimpleString);
DECLPROC(PySys_SetPath);
DECLPROC(PySys_SetArgvEx);
DECLPROC(Py_SetProgramName);
DECLPROC(PyImport_ImportModule);
DECLPROC(PyImport_AddModule);
DECLPROC(PyObject_SetAttrString);
DECLPROC(PyList_New);
DECLPROC(PyList_Append);
DECLPROC(Py_BuildValue);
DECLPROC(PyUnicode_FromString);
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
DECLPROC(PyLong_AsLong);
DECLPROC(PySys_SetObject);


/*
 * Get all of the entry points from libpython
 * that we are interested in.
 */
int pyi_python_map_names(HMODULE dll, int pyvers)
{
    GETVAR(dll, Py_FrozenFlag);
    GETVAR(dll, Py_NoSiteFlag);
    GETVAR(dll, Py_OptimizeFlag);
    GETVAR(dll, Py_VerboseFlag);
    GETVAR(dll, Py_IgnoreEnvironmentFlag);
    GETVAR(dll, Py_DontWriteBytecodeFlag);
    GETVAR(dll, Py_NoUserSiteDirectory);

    GETPROC(dll, Py_Initialize);
    GETPROC(dll, Py_Finalize);
    GETPROCOPT(dll, Py_IncRef);
    GETPROCOPT(dll, Py_DecRef);
    GETPROC(dll, Py_SetPath);
    GETPROC(dll, Py_SetPythonHome);
    GETPROC(dll, PyImport_ExecCodeModule);
    GETPROC(dll, PyRun_SimpleString);
    GETPROC(dll, PyUnicode_FromString);
    GETPROC(dll, PySys_SetPath);
    GETPROC(dll, PySys_SetArgvEx);
    GETPROC(dll, Py_SetProgramName);
    GETPROC(dll, PyImport_ImportModule);
    GETPROC(dll, PyImport_AddModule);
    GETPROC(dll, PyObject_SetAttrString);
    GETPROC(dll, PyList_New);
    GETPROC(dll, PyList_Append);
    GETPROC(dll, Py_BuildValue);
    GETPROC(dll, PyObject_CallFunction);
    GETPROC(dll, PyModule_GetDict);
    GETPROC(dll, PyDict_GetItemString);
    GETPROC(dll, PyErr_Clear);
    GETPROC(dll, PyErr_Occurred);
    GETPROC(dll, PyErr_Print);
    GETPROC(dll, PySys_AddWarnOption);
    GETPROC(dll, PyEval_InitThreads);
    GETPROC(dll, PyEval_AcquireThread);
    GETPROC(dll, PyEval_ReleaseThread);
    GETPROC(dll, PyThreadState_Swap);
    GETPROC(dll, Py_NewInterpreter);
    GETPROC(dll, Py_EndInterpreter);
    GETPROC(dll, PyLong_AsLong);
    GETPROC(dll, PySys_SetObject);

    VS("LOADER: Loaded functions from Python library.\n");

    return 0;
}
