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
 *
 * We use dynamic loading -> one binary can be used with (nearly) any Python
 * version. This is the cruft necessary to do dynamic loading.
 */


#ifndef PYI_PYTHON_H
#define PYI_PYTHON_H


/*
 * These macros used to define variables to hold dynamically accessed entry
 * points. These are declared 'extern' in this header, and defined fully later.
 */
#ifdef WIN32

#define EXTDECLPROC(result, name, args)\
    typedef result (__cdecl *__PROC__##name) args;\
    extern __PROC__##name PI_##name;

#define EXTDECLVAR(vartyp, name)\
    typedef vartyp __VAR__##name;\
    extern __VAR__##name *PI_##name;

#else

#define EXTDECLPROC(result, name, args)\
    typedef result (*__PROC__##name) args;\
    extern __PROC__##name PI_##name;

#define EXTDECLVAR(vartyp, name)\
    typedef vartyp __VAR__##name;\
    extern __VAR__##name *PI_##name;

#endif /* WIN32 */

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
EXTDECLVAR(int, Py_FrozenFlag);
EXTDECLVAR(int, Py_NoSiteFlag);
EXTDECLVAR(int, Py_OptimizeFlag);
EXTDECLVAR(int, Py_VerboseFlag);
EXTDECLPROC(int, Py_Initialize, (void));
EXTDECLPROC(int, Py_Finalize, (void));
EXTDECLPROC(void, Py_IncRef, (PyObject *));
EXTDECLPROC(void, Py_DecRef, (PyObject *));
EXTDECLPROC(void, Py_SetPythonHome, (char *));
EXTDECLPROC(PyObject *, PyImport_ExecCodeModule, (char *, PyObject *));
EXTDECLPROC(int, PyRun_SimpleString, (char *));
EXTDECLPROC(int, PySys_SetArgv, (int, char **));
EXTDECLPROC(void, Py_SetProgramName, (char *));
EXTDECLPROC(PyObject *, PyImport_ImportModule, (char *));
EXTDECLPROC(PyObject *, PyImport_AddModule, (char *));
EXTDECLPROC(int, PyObject_SetAttrString, (PyObject *, char *, PyObject *));
EXTDECLPROC(PyObject *, PyList_New, (int));
EXTDECLPROC(int, PyList_Append, (PyObject *, PyObject *));
EXTDECLPROC(PyObject *, Py_BuildValue, (char *, ...));
EXTDECLPROC(PyObject *, PyString_FromStringAndSize, (const char *, size_t));
EXTDECLPROC(PyObject *, PyFile_FromString, (char *, char *));
EXTDECLPROC(char *, PyString_AsString, (PyObject *));
EXTDECLPROC(PyObject *, PyObject_CallFunction, (PyObject *, char *, ...));
EXTDECLPROC(PyObject *, PyModule_GetDict, (PyObject *));
EXTDECLPROC(PyObject *, PyDict_GetItemString, (PyObject *, char *));
EXTDECLPROC(void, PyErr_Clear, (void) );
EXTDECLPROC(PyObject *, PyErr_Occurred, (void) );
EXTDECLPROC(void, PyErr_Print, (void) );
EXTDECLPROC(PyObject *, PyObject_CallObject, (PyObject *, PyObject*) );
EXTDECLPROC(PyObject *, PyObject_CallMethod, (PyObject *, char *, char *, ...) );
EXTDECLPROC(void, PySys_AddWarnOption, (char *));
EXTDECLPROC(void, PyEval_InitThreads, (void) );
EXTDECLPROC(void, PyEval_AcquireThread, (PyThreadState *) );
EXTDECLPROC(void, PyEval_ReleaseThread, (PyThreadState *) );
EXTDECLPROC(PyThreadState *, PyThreadState_Swap, (PyThreadState *) );
EXTDECLPROC(PyThreadState *, Py_NewInterpreter, (void) );
EXTDECLPROC(void, Py_EndInterpreter, (PyThreadState *) );
EXTDECLPROC(long, PyInt_AsLong, (PyObject *) );
EXTDECLPROC(int, PySys_SetObject, (char *, PyObject *));


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
 */
#ifdef WIN32

#define DECLPROC(name)\
    __PROC__##name PI_##name = NULL;
#define GETPROCOPT(dll, name)\
    PI_##name = (__PROC__##name)GetProcAddress (dll, #name)
#define GETPROC(dll, name)\
    GETPROCOPT(dll, name); \
    if (!PI_##name) {\
        FATALERROR ("Cannot GetProcAddress for " #name);\
        return -1;\
    }
#define DECLVAR(name)\
    __VAR__##name *PI_##name = NULL;
#define GETVAR(dll, name)\
    PI_##name = (__VAR__##name *)GetProcAddress (dll, #name);\
    if (!PI_##name) {\
        FATALERROR ("Cannot GetProcAddress for " #name);\
        return -1;\
    }

#else

#define DECLPROC(name)\
    __PROC__##name PI_##name = NULL;
#define GETPROCOPT(dll, name)\
    PI_##name = (__PROC__##name)dlsym (dll, #name)
#define GETPROC(dll, name)\
    GETPROCOPT(dll, name);\
    if (!PI_##name) {\
        FATALERROR ("Cannot dlsym for " #name);\
        return -1;\
    }
#define DECLVAR(name)\
    __VAR__##name *PI_##name = NULL;
#define GETVAR(dll, name)\
    PI_##name = (__VAR__##name *)dlsym(dll, #name);\
    if (!PI_##name) {\
        FATALERROR ("Cannot dlsym for " #name);\
        return -1;\
    }

#endif /* WIN32 */


int pyi_python_map_names(HMODULE dll, int pyvers);


#endif /* PYI_PYTHON_H */
