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
    #include <windows.h> /* HMODULE */
#else
    #include <dlfcn.h> /* dlsym */
#endif
#include <stddef.h> /* ptrdiff_t */
#include <stdlib.h>

#include "pyi_global.h"
#include "pyi_python.h"


/* Python functions to bind */
PYI_DECLPROC(Py_DecRef)
PYI_DECLPROC(Py_DecodeLocale)
PYI_DECLPROC(Py_ExitStatusException)
PYI_DECLPROC(Py_Finalize)
PYI_DECLPROC(Py_InitializeFromConfig)
PYI_DECLPROC(Py_IsInitialized)
PYI_DECLPROC(Py_PreInitialize)

PYI_DECLPROC(PyConfig_Clear)
PYI_DECLPROC(PyConfig_InitIsolatedConfig)
PYI_DECLPROC(PyConfig_Read)
PYI_DECLPROC(PyConfig_SetBytesString)
PYI_DECLPROC(PyConfig_SetString)
PYI_DECLPROC(PyConfig_SetWideStringList)

PYI_DECLPROC(PyErr_Clear)
PYI_DECLPROC(PyErr_Fetch)
PYI_DECLPROC(PyErr_NormalizeException)
PYI_DECLPROC(PyErr_Occurred)
PYI_DECLPROC(PyErr_Print)
PYI_DECLPROC(PyErr_Restore)

PYI_DECLPROC(PyEval_EvalCode)

PYI_DECLPROC(PyImport_AddModule)
PYI_DECLPROC(PyImport_ExecCodeModule)
PYI_DECLPROC(PyImport_ImportModule)

PYI_DECLPROC(PyMarshal_ReadObjectFromString)

PYI_DECLPROC(PyMem_RawFree)

PYI_DECLPROC(PyModule_GetDict)

PYI_DECLPROC(PyObject_CallFunction)
PYI_DECLPROC(PyObject_CallFunctionObjArgs)
PYI_DECLPROC(PyObject_GetAttrString)
PYI_DECLPROC(PyObject_SetAttrString)
PYI_DECLPROC(PyObject_Str)

PYI_DECLPROC(PyPreConfig_InitIsolatedConfig)

PYI_DECLPROC(PyRun_SimpleStringFlags)

PYI_DECLPROC(PyStatus_Exception)

PYI_DECLPROC(PySys_GetObject)
PYI_DECLPROC(PySys_SetObject)

PYI_DECLPROC(PyUnicode_AsUTF8)
PYI_DECLPROC(PyUnicode_Decode)
PYI_DECLPROC(PyUnicode_DecodeFSDefault)
PYI_DECLPROC(PyUnicode_FromFormat)
PYI_DECLPROC(PyUnicode_FromString)
PYI_DECLPROC(PyUnicode_Join)
PYI_DECLPROC(PyUnicode_Replace)


/*
 * Bind all required functions from python shared library.
 */
int
pyi_python_bind_functions(pyi_dylib_t dll, int python_version)
{
    PYI_GETPROC(dll, Py_DecRef)
    PYI_GETPROC(dll, Py_DecodeLocale)
    PYI_GETPROC(dll, Py_ExitStatusException)
    PYI_GETPROC(dll, Py_Finalize)
    PYI_GETPROC(dll, Py_InitializeFromConfig)
    PYI_GETPROC(dll, Py_IsInitialized)
    PYI_GETPROC(dll, Py_PreInitialize)

    PYI_GETPROC(dll, PyConfig_Clear)
    PYI_GETPROC(dll, PyConfig_InitIsolatedConfig)
    PYI_GETPROC(dll, PyConfig_Read)
    PYI_GETPROC(dll, PyConfig_SetBytesString)
    PYI_GETPROC(dll, PyConfig_SetString)
    PYI_GETPROC(dll, PyConfig_SetWideStringList)

    PYI_GETPROC(dll, PyErr_Clear)
    PYI_GETPROC(dll, PyErr_Fetch)
    PYI_GETPROC(dll, PyErr_NormalizeException)
    PYI_GETPROC(dll, PyErr_Occurred)
    PYI_GETPROC(dll, PyErr_Print)
    PYI_GETPROC(dll, PyErr_Restore)

    PYI_GETPROC(dll, PyEval_EvalCode)

    PYI_GETPROC(dll, PyImport_AddModule)
    PYI_GETPROC(dll, PyImport_ExecCodeModule)
    PYI_GETPROC(dll, PyImport_ImportModule)

    PYI_GETPROC(dll, PyMarshal_ReadObjectFromString)

    PYI_GETPROC(dll, PyMem_RawFree)

    PYI_GETPROC(dll, PyModule_GetDict)

    PYI_GETPROC(dll, PyObject_CallFunction)
    PYI_GETPROC(dll, PyObject_CallFunctionObjArgs)
    PYI_GETPROC(dll, PyObject_GetAttrString)
    PYI_GETPROC(dll, PyObject_SetAttrString)
    PYI_GETPROC(dll, PyObject_Str)

    PYI_GETPROC(dll, PyPreConfig_InitIsolatedConfig)

    PYI_GETPROC(dll, PyRun_SimpleStringFlags)

    PYI_GETPROC(dll, PyStatus_Exception)

    PYI_GETPROC(dll, PySys_GetObject)
    PYI_GETPROC(dll, PySys_SetObject)

    PYI_GETPROC(dll, PyUnicode_AsUTF8)
    PYI_GETPROC(dll, PyUnicode_Decode)
    PYI_GETPROC(dll, PyUnicode_DecodeFSDefault)
    PYI_GETPROC(dll, PyUnicode_FromFormat)
    PYI_GETPROC(dll, PyUnicode_FromString)
    PYI_GETPROC(dll, PyUnicode_Join)
    PYI_GETPROC(dll, PyUnicode_Replace)

    PYI_DEBUG("LOADER: loaded functions from Python shared library.\n");

    return 0;
}
