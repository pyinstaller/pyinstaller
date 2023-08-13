/*
 * ****************************************************************************
 * Copyright (c) 2013-2023, PyInstaller Development Team.
 *
 * Distributed under the terms of the GNU General Public License (version 2
 * or later) with exception for distributing the bootloader.
 *
 * The full license is in the file COPYING.txt, distributed with this software.
 *
 * SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
 * ****************************************************************************
 */

#ifdef _WIN32
#include <windows.h>  /* HMODULE */
#else
#include <dlfcn.h>  /* dlsym */
#endif
#include <stddef.h>  /* ptrdiff_t */
#include <stdlib.h>

#include "pyi_global.h"
#include "pyi_python.h"


/* Python functions to bind */
DECLPROC(Py_DecRef);
DECLPROC(Py_DecodeLocale);
DECLPROC(Py_ExitStatusException);
DECLPROC(Py_Finalize);
DECLPROC(Py_InitializeFromConfig);
DECLPROC(Py_IsInitialized);
DECLPROC(Py_PreInitialize);

DECLPROC(PyConfig_Clear);
DECLPROC(PyConfig_InitIsolatedConfig);
DECLPROC(PyConfig_Read);
DECLPROC(PyConfig_SetBytesString);
DECLPROC(PyConfig_SetString);
DECLPROC(PyConfig_SetWideStringList);

DECLPROC(PyErr_Clear);
DECLPROC(PyErr_Fetch);
DECLPROC(PyErr_NormalizeException);
DECLPROC(PyErr_Occurred);
DECLPROC(PyErr_Print);
DECLPROC(PyErr_Restore);

DECLPROC(PyEval_EvalCode);

DECLPROC(PyImport_AddModule);
DECLPROC(PyImport_ExecCodeModule);
DECLPROC(PyImport_ImportModule);

DECLPROC(PyList_Append);

DECLPROC(PyMarshal_ReadObjectFromString);

DECLPROC(PyMem_RawFree);

DECLPROC(PyModule_GetDict);

DECLPROC(PyObject_CallFunction);
DECLPROC(PyObject_CallFunctionObjArgs);
DECLPROC(PyObject_GetAttrString);
DECLPROC(PyObject_SetAttrString);
DECLPROC(PyObject_Str);

DECLPROC(PyPreConfig_InitIsolatedConfig);

DECLPROC(PyRun_SimpleStringFlags);

DECLPROC(PyStatus_Exception);

DECLPROC(PySys_GetObject);
DECLPROC(PySys_SetObject);

DECLPROC(PyUnicode_AsUTF8);
DECLPROC(PyUnicode_Decode);
DECLPROC(PyUnicode_DecodeFSDefault);
DECLPROC(PyUnicode_FromFormat);
DECLPROC(PyUnicode_FromString);
DECLPROC(PyUnicode_Join);
DECLPROC(PyUnicode_Replace);


/*
 * Bind all required functions from python shared library.
 */
int
pyi_python_bind_functions(HMODULE dll, int pyvers)
{
    GETPROC(dll, Py_DecRef);
    GETPROC(dll, Py_DecodeLocale);
    GETPROC(dll, Py_ExitStatusException);
    GETPROC(dll, Py_Finalize);
    GETPROC(dll, Py_InitializeFromConfig);
    GETPROC(dll, Py_IsInitialized);
    GETPROC(dll, Py_PreInitialize);

    GETPROC(dll, PyConfig_Clear);
    GETPROC(dll, PyConfig_InitIsolatedConfig);
    GETPROC(dll, PyConfig_Read);
    GETPROC(dll, PyConfig_SetBytesString);
    GETPROC(dll, PyConfig_SetString);
    GETPROC(dll, PyConfig_SetWideStringList);

    GETPROC(dll, PyErr_Clear);
    GETPROC(dll, PyErr_Fetch);
    GETPROC(dll, PyErr_NormalizeException);
    GETPROC(dll, PyErr_Occurred);
    GETPROC(dll, PyErr_Print);
    GETPROC(dll, PyErr_Restore);

    GETPROC(dll, PyEval_EvalCode);

    GETPROC(dll, PyImport_AddModule);
    GETPROC(dll, PyImport_ExecCodeModule);
    GETPROC(dll, PyImport_ImportModule);

    GETPROC(dll, PyList_Append);

    GETPROC(dll, PyMarshal_ReadObjectFromString);

    GETPROC(dll, PyMem_RawFree);

    GETPROC(dll, PyModule_GetDict);

    GETPROC(dll, PyObject_CallFunction);
    GETPROC(dll, PyObject_CallFunctionObjArgs);
    GETPROC(dll, PyObject_GetAttrString);
    GETPROC(dll, PyObject_SetAttrString);
    GETPROC(dll, PyObject_Str);

    GETPROC(dll, PyPreConfig_InitIsolatedConfig);

    GETPROC(dll, PyRun_SimpleStringFlags);

    GETPROC(dll, PyStatus_Exception);

    GETPROC(dll, PySys_GetObject);
    GETPROC(dll, PySys_SetObject);

    GETPROC(dll, PyUnicode_AsUTF8);
    GETPROC(dll, PyUnicode_Decode);
    GETPROC(dll, PyUnicode_DecodeFSDefault);
    GETPROC(dll, PyUnicode_FromFormat);
    GETPROC(dll, PyUnicode_FromString);
    GETPROC(dll, PyUnicode_Join);
    GETPROC(dll, PyUnicode_Replace);

    VS("LOADER: Loaded functions from Python library.\n");

    return 0;
}
