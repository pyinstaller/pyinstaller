/*
 * ****************************************************************************
 * Copyright (c) 2013-2018, PyInstaller Development Team.
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
    #include <windows.h>  /* HMODULE */
    #include <winsock.h>  /* ntohl */
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

DECLPROC(PyImport_AddModule);
DECLPROC(PyImport_ExecCodeModule);
DECLPROC(PyImport_ImportModule);
DECLPROC(PyList_Append);
DECLPROC(PyList_New);
DECLPROC(PyLong_AsLong);
DECLPROC(PyModule_GetDict);
DECLPROC(PyObject_CallFunction);
DECLPROC(PyObject_SetAttrString);
DECLPROC(PyRun_SimpleString);
DECLPROC(PyString_FromString);
DECLPROC(PySys_AddWarnOption);
DECLPROC(PySys_SetArgvEx);
DECLPROC(PySys_GetObject);
DECLPROC(PySys_SetObject);
DECLPROC(PySys_SetPath);
DECLPROC(PyUnicode_FromString);

DECLPROC(Py_DecodeLocale);
DECLPROC(PyString_FromFormat);
DECLPROC(PyUnicode_FromFormat);
DECLPROC(PyUnicode_DecodeFSDefault);
DECLPROC(PyUnicode_Decode);

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

    /* functions with prefix `Py_` */
    GETPROC(dll, Py_BuildValue);
    GETPROC(dll, Py_DecRef);
    GETPROC(dll, Py_Finalize);
    GETPROC(dll, Py_IncRef);
    GETPROC(dll, Py_Initialize);

    if (pyvers >= 30) {
        /* new in Python 3 */
        GETPROC(dll, Py_SetPath);
        GETPROC(dll, Py_GetPath);
    }
    ;
    GETPROC(dll, Py_SetProgramName);
    GETPROC(dll, Py_SetPythonHome);

    /* other functions */
    GETPROC(dll, PyDict_GetItemString);
    GETPROC(dll, PyErr_Clear);
    GETPROC(dll, PyErr_Occurred);
    GETPROC(dll, PyErr_Print);
    GETPROC(dll, PyImport_AddModule);
    GETPROC(dll, PyImport_ExecCodeModule);
    GETPROC(dll, PyImport_ImportModule);
    GETPROC(dll, PyList_Append);
    GETPROC(dll, PyList_New);
    GETPROC(dll, PyLong_AsLong);
    GETPROC(dll, PyModule_GetDict);
    GETPROC(dll, PyObject_CallFunction);
    GETPROC(dll, PyObject_SetAttrString);
    GETPROC(dll, PyRun_SimpleString);

    if (pyvers < 30) {
        GETPROC(dll, PyString_FromString);
        GETPROC(dll, PyString_FromFormat);
    }
    ;
    GETPROC(dll, PySys_AddWarnOption);
    GETPROC(dll, PySys_SetArgvEx);
    GETPROC(dll, PySys_GetObject);
    GETPROC(dll, PySys_SetObject);
    GETPROC(dll, PySys_SetPath);
    GETPROC(dll, PyEval_EvalCode);
    GETPROC(dll, PyMarshal_ReadObjectFromString);

    if (pyvers >= 30) {
        /* new in Python 2.6, but not reliable available in all Linux distros */
        GETPROC(dll, PyUnicode_FromString);

        /* _Py_char2wchar is new in Python 3, in Python 3.5 renamed to Py_DecodeLocale */
        if (pyvers >= 35) {
            GETPROC(dll, Py_DecodeLocale);
        }
        else {
            GETPROC_RENAMED(dll, Py_DecodeLocale, _Py_char2wchar);
        };
    }
    ;

    if (pyvers >= 30) {
        /* only used on py3 */
        GETPROC(dll, PyUnicode_FromFormat);
        GETPROC(dll, PyUnicode_Decode);
    }

    if (pyvers >= 32) {
        /* new in Python 3.2 */
        GETPROC(dll, PyUnicode_DecodeFSDefault);
    }

    VS("LOADER: Loaded functions from Python library.\n");

    return 0;
}
