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
#include "pyi_python27_compat.h"

/*
 * These macros used to define variables to hold dynamically accessed entry
 * points. These are declared 'extern' in this header, and defined fully later.
 */
#ifdef _WIN32

    #define EXTDECLPROC(result, name, args) \
    typedef result (__cdecl *__PROC__ ## name) args; \
    extern __PROC__ ## name PI_ ## name;

    #define EXTDECLVAR(vartyp, name) \
    typedef vartyp __VAR__ ## name; \
    extern __VAR__ ## name *PI_ ## name;

#else

    #define EXTDECLPROC(result, name, args) \
    typedef result (*__PROC__ ## name) args; \
    extern __PROC__ ## name PI_ ## name;

    #define EXTDECLVAR(vartyp, name) \
    typedef vartyp __VAR__ ## name; \
    extern __VAR__ ## name *PI_ ## name;

#endif  /* WIN32 */

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
struct _object;
typedef struct _object PyObject;
struct _PyThreadState;
typedef struct _PyThreadState PyThreadState;

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
EXTDECLPROC(int, PyRun_SimpleString, (char *));  /* Py3: UTF-8 encoded string */

/* In Python 3 for these the first argument has to be a UTF-8 encoded string: */
EXTDECLPROC(PyObject *, PyImport_ExecCodeModule, (char *, PyObject *));
EXTDECLPROC(PyObject *, PyImport_ImportModule, (char *));
EXTDECLPROC(PyObject *, PyImport_AddModule, (char *));

EXTDECLPROC(int, PyObject_SetAttrString, (PyObject *, char *, PyObject *));
EXTDECLPROC(PyObject *, PyList_New, (int));
EXTDECLPROC(int, PyList_Append, (PyObject *, PyObject *));
/* Create a new value based on a format string similar to those accepted by the PyArg_Parse*() */
EXTDECLPROC(PyObject *, Py_BuildValue, (char *, ...));
EXTDECLPROC(PyObject *, PyString_FromString, (const char *));
/* Create a Unicode object from the char buffer. The bytes will be interpreted as being UTF-8 encoded. */
EXTDECLPROC(PyObject *, PyUnicode_FromString, (const char *));
EXTDECLPROC(PyObject *, PyObject_CallFunction, (PyObject *, char *, ...));
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

/* Used to add PYZ to sys.path */
EXTDECLPROC(PyObject *, PySys_GetObject, (const char *));
EXTDECLPROC(PyObject *, PyString_FromFormat, (const char *, ...));
EXTDECLPROC(PyObject *, PyUnicode_FromFormat, (const char *, ...));
EXTDECLPROC(PyObject *, PyUnicode_DecodeFSDefault, (const char *));
EXTDECLPROC(PyObject *, PyUnicode_Decode,
            (const char *, size_t, const char *, const char *));                               /* Py_ssize_t */

/* Used to load and execute marshalled code objects */
EXTDECLPROC(PyObject *, PyEval_EvalCode, (PyObject *, PyObject *, PyObject *));
EXTDECLPROC(PyObject *, PyMarshal_ReadObjectFromString, (const char *, size_t));  /* Py_ssize_t */

/*
 * Macros for reference counting through exported functions
 * (that is: without binding to the binary structure of a PyObject.
 * These rely on the Py_IncRef/Py_DecRef API functions on Pyhton 2.4+.
 *
 * Python versions before 2.4 do not export IncRef/DecRef as a binary API,
 * but only as macros in header files. Since we support Python 2.4+ we do not
 * need to provide an emulated incref/decref as it was with older Python
 * versions.
 *
 * We do not want to depend on Python.h for many reasons (including the fact
 * that we would like to have a single binary for all Python versions).
 */

#define Py_XINCREF(o)    PI_Py_IncRef(o)
#define Py_XDECREF(o)    PI_Py_DecRef(o)
#define Py_DECREF(o)     Py_XDECREF(o)
#define Py_INCREF(o)     Py_XINCREF(o)

/* Macros to declare and get Python entry points in the C file.
 * Typedefs '__PROC__...' have been done above
 *
 * GETPROC_RENAMED is to support Python APIs that are simply renamed. We use
 * the new name, and when loading an old Python lib, load the old symbol into the
 * new name.
 */
#ifdef _WIN32

    #define DECLPROC(name) \
    __PROC__ ## name PI_ ## name = NULL;
    #define GETPROCOPT(dll, name, sym) \
    PI_ ## name = (__PROC__ ## name)GetProcAddress (dll, #sym)
    #define GETPROC(dll, name) \
    GETPROCOPT(dll, name, name); \
    if (!PI_ ## name) { \
        FATAL_WINERROR("GetProcAddress", "Failed to get address for " #name "\n");\
        return -1; \
    }
    #define GETPROC_RENAMED(dll, name, sym) \
    GETPROCOPT(dll, name, sym); \
    if (!PI_ ## name) { \
        FATAL_WINERROR("GetProcAddress", "Failed to get address for " #sym "\n");\
        return -1; \
    }
    #define DECLVAR(name) \
    __VAR__ ## name * PI_ ## name = NULL;
    #define GETVAR(dll, name) \
    PI_ ## name = (__VAR__ ## name *)GetProcAddress (dll, #name); \
    if (!PI_ ## name) { \
        FATAL_WINERROR("GetProcAddress", "Failed to get address for " #name "\n");\
        return -1; \
    }

#else /* ifdef _WIN32 */

    #define DECLPROC(name) \
    __PROC__ ## name PI_ ## name = NULL;
    #define GETPROCOPT(dll, name, sym) \
    PI_ ## name = (__PROC__ ## name)dlsym (dll, #sym)
    #define GETPROC(dll, name) \
    GETPROCOPT(dll, name, name); \
    if (!PI_ ## name) { \
        FATALERROR ("Cannot dlsym for " #name "\n"); \
        return -1; \
    }
    #define GETPROC_RENAMED(dll, name, sym) \
    GETPROCOPT(dll, name, sym); \
    if (!PI_ ## name) { \
        FATALERROR ("Cannot dlsym for " #sym "\n"); \
        return -1; \
    }
    #define DECLVAR(name) \
    __VAR__ ## name * PI_ ## name = NULL;
    #define GETVAR(dll, name) \
    PI_ ## name = (__VAR__ ## name *)dlsym(dll, #name); \
    if (!PI_ ## name) { \
        FATALERROR ("Cannot dlsym for " #name "\n"); \
        return -1; \
    }

#endif  /* WIN32 */

int pyi_python_map_names(HMODULE dll, int pyvers);

#endif  /* PYI_PYTHON_H */
