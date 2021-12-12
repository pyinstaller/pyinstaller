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
 *
 * We use dynamic loading -> one binary can be used with (nearly) any Python
 * version. This is the cruft necessary to do dynamic loading.
 */

#ifndef PYI_PYTHON_H
#define PYI_PYTHON_H

#include "pyi_global.h"
#ifdef _WIN32
    #include <windows.h>  /* HMODULE */
#endif
#include <wchar.h>

/*
 * Python.h replacements.
 *
 * We do not want to include Python.h because we do no want to bind
 * to a specific version of Python. If we were to, eg., use the
 * Py_INCREF macro from Python.h, the compiled code would depend
 * on the specific layout in memory of PyObject, and thus change
 * when Python changes (or if your platform changes between 32bit
 * and 64bit). In other words, you wouldn't be able to build a single
 * bootloader working across all Python versions (which is specifically
 * important on Windows).
 *
 * Instead, the bootloader does not depend on the Python ABI at all.
 * It dynamically-load the Python library (after having unpacked it)
 * and bind the exported functions. All Python objects are used as
 * opaque data structures (through pointers only), so the code is
 * fully compatible if the Python data structure layouts change.
 */

/* Forward declarations of opaque Python types. */
struct _PyObject;
typedef struct _PyObject PyObject;
struct _PyThreadState;
typedef struct _PyThreadState PyThreadState;
struct _PyCompilerFlags;
typedef struct _PyCompilerFlags PyCompilerFlags;

/* The actual declarations of var & function entry points used. */

/* Flags. */
EXTDECLVAR(int, Py_FrozenFlag);
EXTDECLVAR(int, Py_NoSiteFlag);
EXTDECLVAR(int, Py_OptimizeFlag);
EXTDECLVAR(const char*, Py_FileSystemDefaultEncoding);
EXTDECLVAR(int, Py_VerboseFlag);
EXTDECLVAR(int, Py_IgnoreEnvironmentFlag);
EXTDECLVAR(int, Py_DontWriteBytecodeFlag);
EXTDECLVAR(int, Py_NoUserSiteDirectory);
EXTDECLVAR(int, Py_UnbufferedStdioFlag);

/* This initializes the table of loaded modules (sys.modules), and creates the fundamental modules builtins, __main__ and sys. It also initializes the module search path (sys.path). It does not set sys.argv; */
EXTDECLPROC(int, Py_Initialize, (void));
/* Undo all initializations made by Py_Initialize() and subsequent use of Python/C API functions, and destroy all sub-interpreters. */
EXTDECLPROC(int, Py_Finalize, (void));

EXTDECLPROC(void, Py_IncRef, (PyObject *));
EXTDECLPROC(void, Py_DecRef, (PyObject *));

/*
 * These functions have to be called before Py_Initialize()
 */
EXTDECLPROC(void, Py_SetProgramName, (wchar_t *));
EXTDECLPROC(void, Py_SetPythonHome, (wchar_t *));
EXTDECLPROC(void, Py_SetPath, (wchar_t *));  /* new in Python 3 */
EXTDECLPROC(wchar_t *, Py_GetPath, (void));  /* new in Python 3 */

EXTDECLPROC(void, PySys_SetPath, (wchar_t *));
EXTDECLPROC(int, PySys_SetArgvEx, (int, wchar_t **, int));
EXTDECLPROC(int, PyRun_SimpleStringFlags, (const char *, PyCompilerFlags *));  /* Py3: UTF-8 encoded string */

/* In Python 3 for these the first argument has to be a UTF-8 encoded string: */
EXTDECLPROC(PyObject *, PyImport_ExecCodeModule, (char *, PyObject *));
EXTDECLPROC(PyObject *, PyImport_ImportModule, (char *));
EXTDECLPROC(PyObject *, PyImport_AddModule, (char *));

EXTDECLPROC(int, PyObject_SetAttrString, (PyObject *, char *, PyObject *));
EXTDECLPROC(PyObject *, PyList_New, (int));
EXTDECLPROC(int, PyList_Append, (PyObject *, PyObject *));
/* Create a new value based on a format string similar to those accepted by the PyArg_Parse*() */
EXTDECLPROC(PyObject *, Py_BuildValue, (char *, ...));
/* Create a Unicode object from the char buffer. The bytes will be interpreted as being UTF-8 encoded. */
EXTDECLPROC(PyObject *, PyUnicode_FromString, (const char *));
EXTDECLPROC(PyObject *, PyObject_CallFunction, (PyObject *, char *, ...));
EXTDECLPROC(PyObject *, PyObject_CallFunctionObjArgs, (PyObject *, ...));
EXTDECLPROC(PyObject *, PyModule_GetDict, (PyObject *));
EXTDECLPROC(PyObject *, PyDict_GetItemString, (PyObject *, char *));
EXTDECLPROC(void, PyErr_Clear, (void) );
EXTDECLPROC(PyObject *, PyErr_Occurred, (void) );
EXTDECLPROC(void, PyErr_Print, (void) );
EXTDECLPROC(void, PySys_AddWarnOption, (wchar_t *));
/* Return a C long representation of the contents of pylong. */
EXTDECLPROC(long, PyLong_AsLong, (PyObject *) );

EXTDECLPROC(int, PySys_SetObject, (char *, PyObject *));

/*
 * Used to convert argv to wchar_t on Linux/OS X
 * On Python 3.0-3.4, this function was called _Py_char2wchar
 */
EXTDECLPROC(wchar_t *, Py_DecodeLocale, (char *, size_t *));
EXTDECLPROC(void, PyMem_RawFree, (void *));

/* Used to add PYZ to sys.path */
EXTDECLPROC(PyObject *, PySys_GetObject, (const char *));
EXTDECLPROC(PyObject *, PyUnicode_FromFormat, (const char *, ...));
EXTDECLPROC(PyObject *, PyUnicode_DecodeFSDefault, (const char *));
EXTDECLPROC(PyObject *, PyUnicode_Decode,
            (const char *, size_t, const char *, const char *));                               /* Py_ssize_t */

/* Used to load and execute marshalled code objects */
EXTDECLPROC(PyObject *, PyEval_EvalCode, (PyObject *, PyObject *, PyObject *));
EXTDECLPROC(PyObject *, PyMarshal_ReadObjectFromString, (const char *, size_t));  /* Py_ssize_t */

/* Used to get traceback information while launching run scripts */
EXTDECLPROC(void, PyErr_Fetch, (PyObject **, PyObject **, PyObject **));
EXTDECLPROC(void, PyErr_Restore, (PyObject *, PyObject *, PyObject *));
EXTDECLPROC(void, PyErr_NormalizeException, (PyObject **, PyObject **, PyObject **));
EXTDECLPROC(PyObject *, PyObject_Str, (PyObject *));
EXTDECLPROC(PyObject *, PyObject_GetAttrString, (PyObject *, const char *));
EXTDECLPROC(const char *, PyUnicode_AsUTF8, (PyObject *));
EXTDECLPROC(PyObject *, PyUnicode_Join, (PyObject *, PyObject *));
EXTDECLPROC(PyObject *, PyUnicode_Replace, (PyObject *, PyObject *, PyObject *, size_t));  /* Py_ssize_t */

int pyi_python_map_names(HMODULE dll, int pyvers);

#endif  /* PYI_PYTHON_H */
