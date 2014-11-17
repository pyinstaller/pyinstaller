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


#ifdef WIN32
    #include <windows.h>
    #include <winsock.h>  // ntohl
#else
    #include <dlfcn.h>  // dlsym
#endif
#include <stddef.h>  // ptrdiff_t
#include <stdlib.h>


/* PyInstaller headers. */
#include "stb.h"
#include "pyi_global.h"
#include "pyi_python.h"


/*
 * Python Entry point declarations (see macros in pyi_python.h).
 */
DECLVAR(Py_FrozenFlag);
DECLVAR(Py_NoSiteFlag);
DECLVAR(Py_OptimizeFlag);
DECLVAR(Py_FileSystemDefaultEncoding);
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


/*
 * Get all of the entry points from libpython
 * that we are interested in.
 */
int pyi_python_map_names(HMODULE dll, int pyvers)
{
    GETVAR(dll, Py_FrozenFlag);
    GETVAR(dll, Py_NoSiteFlag);
    GETVAR(dll, Py_OptimizeFlag);
    GETVAR(dll, Py_FileSystemDefaultEncoding);
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
