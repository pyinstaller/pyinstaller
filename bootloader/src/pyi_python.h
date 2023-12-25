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

/*
 * Python.h replacements.
 *
 * We use dynamic loading -> one binary can be used with (nearly) any Python
 * version. This is the cruft necessary to do dynamic loading.
 */

#ifndef PYI_PYTHON_H
#define PYI_PYTHON_H

#include "pyi_global.h"
#include <wchar.h>


/* Bind all required functions from python shared library */
int pyi_python_bind_functions(pyi_dylib_t dll, int python_version);

/*
 * Python.h replacements.
 *
 * We do not include Python.h because we want to avoid binding to a
 * specific version of Python. For example, if we used the Py_INCREF
 * macro from Python.h, the compiled code would depend on the specific
 * in-memory layout of PyObject, and thus change between Python versions
 * (and between 32-bit and 64-bit architectures). That would make it
 * impossible to build a single bootloader executable that works across
 * all Python version (which is especially important on Windows).
 *
 * Instead, the bootloader does its best to avoid depending on the Python
 * API exported by Python.h header. Instead, it dynamically loads the
 * collected Python shared library (after having unpacked it, if necessary)
 * and binds the exported functions that it requires. Wherever possible,
 * Python objects are used as opaque data structures (passed via pointers
 * only) to ensure that the code is invariant to the layout changes of
 * Python data structures.
 *
 * Well, at least that was the plan, and that is how things were in the
 * days of yore. Then came along PEP 587 with new python initialization
 * configuration API, and those days are but a distant memory now...
 *
 * The new configuration API requires us to allocate the config structure
 * ourselves, so we need to know its size. And we also need to know its
 * layout, because the fields in the structure need to be accessed (set)
 * directly. So if we want to keep avoiding using Python.h and building
 * bootloader for each python version, we need to provide the configuration
 * structure layouts for all supported python versions.
 */

/* Forward declarations of opaque Python types. */
typedef struct _PyObject PyObject;
typedef struct _PyThreadState PyThreadState;
typedef struct _PyCompilerFlags PyCompilerFlags;


/* Strictly speaking, Py_ssize_t should be mapped to ssize_t wherever
 * possible, but for portability reasons, we use size_t. We are primarily
 * concerned about the storage size, not the signedness.
 */
typedef size_t Py_ssize_t;


/* Definitions of configuration structure layouts. These are not opaque,
 * because we need to allocate them, and manipulate with their fields.
 *
 * The original definitions can be found in the include/cpython/initconfig.h
 *
 * For the sake of brevity, our variants do not include the comments.
 *
 * In the original structures, some fields are guarded with MS_WINDOWS
 * define. We map it to our _WIN32 define, because MS_WINDOWS appears
 * to be defined in all Windows build; either directly via customized
 * pyconfig.h header (python.org and Anaconda builds) or due to
 * modifications in pyport.h header (msys2/mingw32 and msys2/mingw64).
 */

#ifdef _WIN32
    #define MS_WINDOWS
#endif

/* This structure is returned from functions by value, so we need to know
 * its layout. At the time of writing, it remains unchanged between the
 * supported python versions.
 */
typedef struct {
    enum {
        _PyStatus_TYPE_OK=0,
        _PyStatus_TYPE_ERROR=1,
        _PyStatus_TYPE_EXIT=2
    } _type;
    const char *func;
    const char *err_msg;
    int exitcode;
} PyStatus;


/* This structure is embedded in the configuration structure, so we need
 * to know its layout. At the time of writing, it remains unchanged between
 * the supported python versions.
 */
typedef struct {
    Py_ssize_t length;
    wchar_t **items;
} PyWideStringList;


/* The PyPreConfig structure. At the time of writing, it remains unchanged
 * between the supported python versions; but in anticipation of future
 * changes, we name our commonly-used layout with _Common suffix.
 */
typedef struct {
    int _config_init;
    int parse_argv;
    int isolated;
    int use_environment;
    int configure_locale;
    int coerce_c_locale;
    int coerce_c_locale_warn;
#ifdef MS_WINDOWS
    int legacy_windows_fs_encoding;
#endif
    int utf8_mode;
    int dev_mode;
    int allocator;
} PyPreConfig_Common;

/* The opaque type used with functions that accept pointer */
typedef struct _PyPreConfig PyPreConfig;


/* Keep configuration structures in separate header */
#include "pyi_pyconfig_v38.h"
#include "pyi_pyconfig_v39.h"
#include "pyi_pyconfig_v310.h"
#include "pyi_pyconfig_v311.h"
#include "pyi_pyconfig_v312.h"
#include "pyi_pyconfig_v313.h"

/* The opaque type used with functions that accept pointer */
typedef struct _PyConfig PyConfig;


/* Py_ */
PYI_EXTDECLPROC(void, Py_DecRef, (PyObject *))
PYI_EXTDECLPROC(wchar_t *, Py_DecodeLocale, (const char *, size_t *))
PYI_EXTDECLPROC(void, Py_ExitStatusException, (PyStatus))
PYI_EXTDECLPROC(int, Py_Finalize, (void))
PYI_EXTDECLPROC(PyStatus, Py_InitializeFromConfig, (PyConfig *))
PYI_EXTDECLPROC(int, Py_IsInitialized, (void))
PYI_EXTDECLPROC(PyStatus, Py_PreInitialize, (const PyPreConfig *))

/* PyConfig_ */
PYI_EXTDECLPROC(void, PyConfig_Clear, (PyConfig *))
PYI_EXTDECLPROC(void, PyConfig_InitIsolatedConfig, (PyConfig *))
PYI_EXTDECLPROC(PyStatus, PyConfig_Read, (PyConfig *))
PYI_EXTDECLPROC(PyStatus, PyConfig_SetBytesString, (PyConfig *, wchar_t **, const char *))
PYI_EXTDECLPROC(PyStatus, PyConfig_SetString, (PyConfig *, wchar_t **, const wchar_t *))
PYI_EXTDECLPROC(PyStatus, PyConfig_SetWideStringList, (PyConfig *, PyWideStringList *, Py_ssize_t, wchar_t **))

/* PyErr_ */
PYI_EXTDECLPROC(void, PyErr_Clear, (void) )
PYI_EXTDECLPROC(void, PyErr_Fetch, (PyObject **, PyObject **, PyObject **))
PYI_EXTDECLPROC(void, PyErr_NormalizeException, (PyObject **, PyObject **, PyObject **))
PYI_EXTDECLPROC(PyObject *, PyErr_Occurred, (void) )
PYI_EXTDECLPROC(void, PyErr_Print, (void) )
PYI_EXTDECLPROC(void, PyErr_Restore, (PyObject *, PyObject *, PyObject *))

/* PyEval */
PYI_EXTDECLPROC(PyObject *, PyEval_EvalCode, (PyObject *, PyObject *, PyObject *))

/* PyImport_ */
PYI_EXTDECLPROC(PyObject *, PyImport_AddModule, (const char *))
PYI_EXTDECLPROC(PyObject *, PyImport_ExecCodeModule, (const char *, PyObject *))
PYI_EXTDECLPROC(PyObject *, PyImport_ImportModule, (const char *))

/* PyMarshal_ */
PYI_EXTDECLPROC(PyObject *, PyMarshal_ReadObjectFromString, (const char *, Py_ssize_t))

/* PyMem_ */
PYI_EXTDECLPROC(void, PyMem_RawFree, (void *))

/* PyModule_ */
PYI_EXTDECLPROC(PyObject *, PyModule_GetDict, (PyObject *))

/* PyObject_ */
PYI_EXTDECLPROC(PyObject *, PyObject_CallFunction, (PyObject *, char *, ...))
PYI_EXTDECLPROC(PyObject *, PyObject_CallFunctionObjArgs, (PyObject *, ...))
PYI_EXTDECLPROC(PyObject *, PyObject_GetAttrString, (PyObject *, const char *))
PYI_EXTDECLPROC(int, PyObject_SetAttrString, (PyObject *, char *, PyObject *))
PYI_EXTDECLPROC(PyObject *, PyObject_Str, (PyObject *))

/* PyPreConfig_ */
PYI_EXTDECLPROC(void, PyPreConfig_InitIsolatedConfig, (PyPreConfig *))

/* PyRun_ */
PYI_EXTDECLPROC(int, PyRun_SimpleStringFlags, (const char *, PyCompilerFlags *))

/* PyStatus_ */
PYI_EXTDECLPROC(int, PyStatus_Exception, (PyStatus))

/* PySys_ */
PYI_EXTDECLPROC(PyObject *, PySys_GetObject, (const char *))
PYI_EXTDECLPROC(int, PySys_SetObject, (const char *, PyObject *))

/* PyUnicode_ */
PYI_EXTDECLPROC(const char *, PyUnicode_AsUTF8, (PyObject *))
PYI_EXTDECLPROC(PyObject *, PyUnicode_Decode, (const char *, Py_ssize_t, const char *, const char *))
PYI_EXTDECLPROC(PyObject *, PyUnicode_DecodeFSDefault, (const char *))
PYI_EXTDECLPROC(PyObject *, PyUnicode_FromFormat, (const char *, ...))
PYI_EXTDECLPROC(PyObject *, PyUnicode_FromString, (const char *))
PYI_EXTDECLPROC(PyObject *, PyUnicode_Join, (PyObject *, PyObject *))
PYI_EXTDECLPROC(PyObject *, PyUnicode_Replace, (PyObject *, PyObject *, PyObject *, Py_ssize_t))


#endif /* PYI_PYTHON_H */
