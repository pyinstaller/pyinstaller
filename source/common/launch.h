/*
 * Launch a python module from an archive.   
 * Copyright (C) 2005, Giovanni Bajo
 * Based on previous work under copyright (c) 2002 McMillan Enterprises, Inc.
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; either version 2
 * of the License, or (at your option) any later version.
 *
 * In addition to the permissions in the GNU General Public License, the
 * authors give you unlimited permission to link or embed the compiled
 * version of this file into combinations with other programs, and to
 * distribute those combinations without any restriction coming from the
 * use of this file. (The General Public License restrictions do apply in
 * other respects; for example, they cover modification of the file, and
 * distribution when not linked into a combine executable.)
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA
 */
#ifndef LAUNCH_H
#define LAUNCH_H
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#ifdef WIN32
#include <io.h>
#else
#include <unistd.h>
#endif
#include <fcntl.h> 
#ifdef WIN32
#include <winsock.h> /* for ntohl */
#else
#include <netinet/in.h>
#endif

/* On Windows, we use dynamic loading so one binary 
   can be used with (nearly) any Python version.
   This is the cruft necessary to do Windows dynamic loading
*/

#ifdef WIN32
/*
 * These macros used to define variables to hold dynamically accessed entry 
 * points. These are declared 'extern' in this header, and defined fully later.
 */
#define EXTDECLPROC(result, name, args)\
    typedef result (__cdecl *__PROC__##name) args;\
    extern __PROC__##name name;

#define EXTDECLVAR(vartyp, name)\
    typedef vartyp __VAR__##name;\
    extern __VAR__##name *name;

/* 
 * These types and macros are included from the Python header file object.h
 * They are needed to do very basic Python functionality.
 */
typedef _typeobject;
typedef struct _object {
    int ob_refcnt; 
    struct _typeobject *ob_type;
} PyObject;
typedef void (*destructor)(PyObject *);
typedef struct _typeobject {
    int ob_refcnt; 
    struct _typeobject *ob_type;
    int ob_size; 
    char *tp_name; /* For printing */
    int tp_basicsize, tp_itemsize; /* For allocation */
    destructor tp_dealloc;
    /* ignore the rest.... */
} PyTypeObject;
struct _ts; /* forward */
typedef struct _is {
    struct _is *next;
    struct _ts *tstate_head;
    PyObject *modules;
    PyObject *sysdict;
    PyObject *builtins;
    int checkinterval;
} PyInterpreterState;
typedef struct _ts {
    struct _ts *next;
    PyInterpreterState *interp;
    void *frame; /* struct _frame *frame; */
    int recursion_depth;
    int ticker;
    int tracing;
    PyObject *sys_profilefunc;
    PyObject *sys_tracefunc;
    PyObject *curexc_type;
    PyObject *curexc_value;
    PyObject *curexc_traceback;
    PyObject *exc_type;
    PyObject *exc_value;
    PyObject *exc_traceback;
    PyObject *dict;
    /* XXX signal handlers should also be here */
} PyThreadState;


/* These are the non reference debugging version of Py_INCREF and DECREF */
#define _Py_Dealloc(op) (*(op)->ob_type->tp_dealloc)((PyObject *)(op))
#define Py_INCREF(op) ((op)->ob_refcnt++)
#define Py_DECREF(op) \
    if (--(op)->ob_refcnt != 0) \
        ; \
    else \
        _Py_Dealloc((PyObject *)(op))
#define Py_XINCREF(op) if ((op) == NULL) ; else Py_INCREF(op)
#define Py_XDECREF(op) if ((op) == NULL) ; else Py_DECREF(op)

/* The actual declarations of var & function entry points used. */
EXTDECLVAR(int, Py_NoSiteFlag);
EXTDECLVAR(int, Py_OptimizeFlag);
EXTDECLVAR(int, Py_VerboseFlag);
EXTDECLPROC(int, Py_Initialize, (void));
EXTDECLPROC(int, Py_Finalize, (void));
EXTDECLPROC(PyObject *, Py_CompileString, (char *, char *, int));
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
EXTDECLPROC(PyObject *, PyFile_FromString, (char *, char *));
EXTDECLPROC(PyObject *, PyString_FromStringAndSize, (const char *, int));
EXTDECLPROC(PyObject *, PyObject_CallFunction, (PyObject *, char *, ...));
EXTDECLPROC(PyObject *, PyModule_GetDict, (PyObject *));
EXTDECLPROC(PyObject *, PyDict_GetItemString, (PyObject *, char *));
EXTDECLPROC(void, PyErr_Clear, () );
EXTDECLPROC(PyObject *, PyErr_Occurred, () );
EXTDECLPROC(void, PyErr_Print, () );
EXTDECLPROC(PyObject *, PyObject_CallObject, (PyObject *, PyObject*) );
EXTDECLPROC(PyObject *, PyObject_CallMethod, (PyObject *, char *, char *, ...) );
EXTDECLPROC(void, PySys_AddWarnOption, (char *)); 
EXTDECLPROC(void, PyEval_InitThreads, () );
EXTDECLPROC(void, PyEval_AcquireThread, (PyThreadState *) );
EXTDECLPROC(void, PyEval_ReleaseThread, (PyThreadState *) );
EXTDECLPROC(void, PyEval_AcquireLock, (void) );
EXTDECLPROC(void, PyEval_ReleaseLock, (void) );
EXTDECLPROC(PyThreadState *, PyThreadState_Swap, (PyThreadState *) );
EXTDECLPROC(PyThreadState *, PyThreadState_New, (PyInterpreterState *) );
EXTDECLPROC(void, PyThreadState_Clear, (PyThreadState *) );
EXTDECLPROC(void, PyThreadState_Delete, (PyThreadState *) );
EXTDECLPROC(PyInterpreterState *, PyInterpreterState_New, () );
EXTDECLPROC(PyThreadState *, Py_NewInterpreter, () );
EXTDECLPROC(void, Py_EndInterpreter, (PyThreadState *) );
EXTDECLPROC(void, PyErr_Print, () );
EXTDECLPROC(long, PyInt_AsLong, (PyObject *) );
EXTDECLPROC(int, PySys_SetObject, (char *, PyObject *));

/* Macros to declare and get Python entry points in the C file.
 * Typedefs '__PROC__...' have been done above
 */
#define DECLPROC(name)\
    __PROC__##name name = NULL;
#define GETPROC(dll, name)\
    name = (__PROC__##name)GetProcAddress (dll, #name);\
    if (!name) {\
        FATALERROR ("Cannot GetProcAddress for " #name);\
        return -1;\
    }
#define DECLVAR(name)\
    __VAR__##name *name = NULL;
#define GETVAR(dll, name)\
    name = (__VAR__##name *)GetProcAddress (dll, #name);\
    if (!name) {\
        FATALERROR ("Cannot GetProcAddress for " #name);\
        return -1;\
    }
#else
#include <Python.h>
#endif /* WIN32 dynamic load cruft */

/*
 * #defines
 */
#define MAGIC "MEI\014\013\012\013\016"    

#if !defined WIN32 && !defined _CONSOLE
#define _CONSOLE
#endif

#ifdef _CONSOLE
# define FATALERROR(x) printf(x)
# define OTHERERROR(x) printf(x)
#else
# define FATALERROR(x) MessageBox(NULL, x, "Fatal Error!", MB_OK | MB_ICONEXCLAMATION)
# define OTHERERROR(x) MessageBox(NULL, x, "Error!", MB_OK | MB_ICONWARNING)
#endif

#ifdef LAUNCH_DEBUG
# ifdef _CONSOLE
#  define VS(arg) printf(arg)
# else
#  define VS(arg) MessageBox(NULL, arg, "Tracing", MB_OK)
# endif
#else
# define VS(arg) 
#endif

/* TOC entry for a CArchive */
typedef struct _toc {
    int structlen;    /*len of this one - including full len of name */
    int pos;          /* pos rel to start of concatenation */
    int len;          /* len of the data (compressed) */
    int ulen;         /* len of data (uncompressed) */
    char cflag;       /* is it compressed (really a byte) */
    char typcd;       /* 'b' binary, 'z' zlib, 'm' module, 's' script (v3), 
					     'x' data, 'o' runtime option  */
    char name[1];    /* the name to save it as */
	/* starting in v5, we stretch this out to a mult of 16 */
} TOC;

/* The CArchive Cookie, from end of the archive. */
typedef struct _cookie {
    char magic[8]; /* 'MEI\014\013\012\013\016' */
    int  len;      /* len of entire package */
    int  TOC;      /* pos (rel to start) of TableOfContents */
    int  TOClen;   /* length of TableOfContents */
    int  pyvers;   /* new in v4 */
} COOKIE;

/* _MAX_PATH for non-Windows */
#ifndef _MAX_PATH
#define _MAX_PATH 256
#endif

/**
 * Load Python using code stored in the following archive.
 * Intended for use by embedding applications.
 *
 * @param archivePath  The path to the archive directory, with trailing 
 *                     backslash. This directory will also contain the binary 
 *                     dependencies of the application. There can be no
 *                     binaries inside the archive.
 *
 * @param archiveName  The file name of the archive, without a path.
 *
 * @return 0 on success, non-zero otherwise.
 *
 */
int launchembedded(char const * archivePath, char  const * archiveName);

/*****************************************************************
 * The following 4 entries are for applications which may need to 
 * use to 2 steps to execute
 *****************************************************************/

/**
 * Initialize the paths and open the archive 
 *
 * @param archivePath  The path (with trailing backslash) to the archive.
 *
 * @param archiveName  The file name of the archive, without a path.
 *
 * @param workpath     The path (with trailing backslash) to where
 *                     the binaries were extracted. If they have not
 *                     benn extracted yet, this is NULL. If they have,
 *                     this will either be archivePath, or a temp dir
 *                     where the user has write permissions.
 *
 * @return 0 on success, non-zero otherwise.
 */
int init(char const * archivePath, char  const * archiveName, char const * workpath);

/**
 * Extract binaries in the archive
 *
 * @param workpath     (OUT) Where the binaries were extracted to. If
 *                      none extracted, is NULL.
 *
 * @return 0 on success, non-zero otherwise.
 */
int extractBinaries(char **workpath);

/**
 * Load Python and execute all scripts in the archive
 * 
 * @param argc			Count of "commandline" args
 * 
 * @param argv			The "commandline".
 *
 * @return -1 for internal failures, or the rc of the last script.
 */
int doIt(int argc, char *argv[]);

/*
 * Call a simple "int func(void)" entry point.  Assumes such a function
 * exists in the main namespace.
 * Return non zero on failure, with -2 if the specific error is
 * that the function does not exist in the namespace.
 *
 * @param name		Name of the function to execute.
 * @param presult	Integer return value.
 */
int callSimpleEntryPoint(char *name, int *presult);

/**
 * Clean up extracted binaries
 */
void cleanUp(void);

/**
 * Helpers for embedders
 */
int getPyVersion(void);
void finalizePython(void);

/**
 * The gory detail level
 */
int setPaths(char const * archivePath, char const * archiveName);
int openArchive(void);
int attachPython(int *loadedNew);
int loadPython(void); /* note - attachPython will call this if not already loaded */
void acquirePythonThread(void);
void releasePythonThread(void);
int startPython(int argc, char *argv[]);
int importModules(void);
int installZlibs(void);
int runScripts(void);
TOC *getFirstTocEntry(void);
TOC *getNextTocEntry(TOC *entry);
void clear(const char *dir);
#endif

