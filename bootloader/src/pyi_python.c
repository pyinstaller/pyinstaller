/*
 * ****************************************************************************
 * Copyright (c) 2013-2021, PyInstaller Development Team.
 *
 * Distributed under the terms of the GNU General Public License (version 2
 * or later) with exception for distributing the bootloader.
 *
 * The full license is in the file COPYING.txt, distributed with this software.
 *
 * SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
 * ****************************************************************************
 */

/*
 * Python.h replacements.
 */

#ifdef _WIN32
    #include <windows.h>  /* HMODULE */
#else
    #include <dlfcn.h>  /* dlsym */
#endif
#include <stddef.h>  /* ptrdiff_t */
#include <stdlib.h>

/* PyInstaller headers. */
#include "pyi_global.h"
#include "pyi_python.h"

/*
 * Python Entry point declarations (see macros in pyi_python.h).
 */
/* external variables */
DECLVAR(Py_DontWriteBytecodeFlag);
DECLVAR(Py_FileSystemDefaultEncoding);
DECLVAR(Py_FrozenFlag);
DECLVAR(Py_IgnoreEnvironmentFlag);
DECLVAR(Py_NoSiteFlag);
DECLVAR(Py_NoUserSiteDirectory);
DECLVAR(Py_OptimizeFlag);
DECLVAR(Py_VerboseFlag);
DECLVAR(Py_UnbufferedStdioFlag);

/* functions with prefix `Py_` */
DECLPROC(Py_BuildValue);
DECLPROC(Py_DecRef);
DECLPROC(Py_Finalize);
DECLPROC(Py_IncRef);
DECLPROC(Py_Initialize);
DECLPROC(Py_SetPath);
DECLPROC(Py_GetPath);
DECLPROC(Py_SetProgramName);
DECLPROC(Py_SetPythonHome);

/* other functions */
DECLPROC(PyDict_GetItemString);
DECLPROC(PyErr_Clear);
DECLPROC(PyErr_Occurred);
DECLPROC(PyErr_Print);
DECLPROC(PyErr_Fetch);
DECLPROC(PyErr_Restore);
DECLPROC(PyErr_NormalizeException);

DECLPROC(PyImport_AddModule);
DECLPROC(PyImport_ExecCodeModule);
DECLPROC(PyImport_ImportModule);
DECLPROC(PyList_Append);
DECLPROC(PyList_New);
DECLPROC(PyLong_AsLong);
DECLPROC(PyModule_GetDict);
DECLPROC(PyObject_CallFunction);
DECLPROC(PyObject_CallFunctionObjArgs);
DECLPROC(PyObject_SetAttrString);
DECLPROC(PyObject_GetAttrString);
DECLPROC(PyObject_Str);
DECLPROC(PyRun_SimpleStringFlags);
DECLPROC(PySys_AddWarnOption);
DECLPROC(PySys_SetArgvEx);
DECLPROC(PySys_GetObject);
DECLPROC(PySys_SetObject);
DECLPROC(PySys_SetPath);
DECLPROC(PyUnicode_FromString);

DECLPROC(Py_DecodeLocale);
DECLPROC(PyMem_RawFree);
DECLPROC(PyUnicode_FromFormat);
DECLPROC(PyUnicode_DecodeFSDefault);
DECLPROC(PyUnicode_Decode);
DECLPROC(PyUnicode_AsUTF8);
DECLPROC(PyUnicode_Join);
DECLPROC(PyUnicode_Replace);

DECLPROC(PyEval_EvalCode);
DECLPROC(PyMarshal_ReadObjectFromString);

/*
 * Get all of the entry points from libpython
 * that we are interested in.
 */
int
pyi_python_map_names(HMODULE dll, int pyvers)
{
    GETVAR(dll, Py_DontWriteBytecodeFlag);
    GETVAR(dll, Py_FileSystemDefaultEncoding);
    GETVAR(dll, Py_FrozenFlag);
    GETVAR(dll, Py_IgnoreEnvironmentFlag);
    GETVAR(dll, Py_NoSiteFlag);
    GETVAR(dll, Py_NoUserSiteDirectory);
    GETVAR(dll, Py_OptimizeFlag);
    GETVAR(dll, Py_VerboseFlag);
    GETVAR(dll, Py_UnbufferedStdioFlag);

    /* functions with prefix `Py_` */
    GETPROC(dll, Py_BuildValue);
    GETPROC(dll, Py_DecRef);
    GETPROC(dll, Py_Finalize);
    GETPROC(dll, Py_IncRef);
    GETPROC(dll, Py_Initialize);

    GETPROC(dll, Py_SetPath);
    GETPROC(dll, Py_GetPath);
    GETPROC(dll, Py_SetProgramName);
    GETPROC(dll, Py_SetPythonHome);

    /* other functions */
    GETPROC(dll, PyDict_GetItemString);
    GETPROC(dll, PyErr_Clear);
    GETPROC(dll, PyErr_Occurred);
    GETPROC(dll, PyErr_Print);
    GETPROC(dll, PyErr_Fetch);
    GETPROC(dll, PyErr_Restore);
    GETPROC(dll, PyErr_NormalizeException);
    GETPROC(dll, PyImport_AddModule);
    GETPROC(dll, PyImport_ExecCodeModule);
    GETPROC(dll, PyImport_ImportModule);
    GETPROC(dll, PyList_Append);
    GETPROC(dll, PyList_New);
    GETPROC(dll, PyLong_AsLong);
    GETPROC(dll, PyModule_GetDict);
    GETPROC(dll, PyObject_CallFunction);
    GETPROC(dll, PyObject_CallFunctionObjArgs);
    GETPROC(dll, PyObject_SetAttrString);
    GETPROC(dll, PyObject_GetAttrString);
    GETPROC(dll, PyObject_Str);

    GETPROC(dll, PyRun_SimpleStringFlags);

    GETPROC(dll, PySys_AddWarnOption);
    GETPROC(dll, PySys_SetArgvEx);
    GETPROC(dll, PySys_GetObject);
    GETPROC(dll, PySys_SetObject);
    GETPROC(dll, PySys_SetPath);
    GETPROC(dll, PyEval_EvalCode);
    GETPROC(dll, PyMarshal_ReadObjectFromString);

    GETPROC(dll, PyUnicode_FromString);

    GETPROC(dll, Py_DecodeLocale);
    GETPROC(dll, PyMem_RawFree);

    GETPROC(dll, PyUnicode_FromFormat);
    GETPROC(dll, PyUnicode_Decode);
    GETPROC(dll, PyUnicode_DecodeFSDefault);
    GETPROC(dll, PyUnicode_AsUTF8);
    GETPROC(dll, PyUnicode_Join);
    GETPROC(dll, PyUnicode_Replace);

    VS("LOADER: Loaded functions from Python library.\n");

    return 0;
}
