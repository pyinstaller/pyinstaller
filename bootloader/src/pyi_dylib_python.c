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

#include <stdlib.h> /* calloc */

#include "pyi_global.h"
#include "pyi_dylib_python.h"
#include "pyi_utils.h"


/* Load the shared library (different codepath for Windows and POSIX) */
#ifdef _WIN32

static int _pyi_dylib_python_load_library(
    struct DYLIB_PYTHON *dylib,
    const char *root_directory_utf8,
    const char *python_libname
)
{
    wchar_t root_directory[PYI_PATH_MAX];
    wchar_t dll_fullpath[PYI_PATH_MAX];

    if (pyi_win32_utf8_to_wcs(root_directory_utf8, root_directory, PYI_PATH_MAX) == NULL) {
        PYI_ERROR_W(L"Failed to convert root directory path to wide-char string.\n");
        return -1;
    }

    /* If ucrtbase.dll exists in top-level application directory, load
     * it proactively before Python library loading to avoid Python library
     * loading failure (unresolved symbol errors) on systems with Universal
     * CRT update not installed.
     *
     * NOTE: this has no effect on contemporary Windows 10/11 systems,
     * because the OS disallows loading of non-system ucrtbase.dll. But
     * it might have been necessary on older Windows versions, so until
     * we explicitly drop support for those, keep this in. See:
     * https://learn.microsoft.com/en-us/cpp/windows/universal-crt-deployment?view=msvc-160#local-deployment
     */
    if (swprintf(dll_fullpath, PYI_PATH_MAX, L"%ls\\ucrtbase.dll", root_directory) >= PYI_PATH_MAX) {
        PYI_ERROR_W(L"Path of ucrtbase.dll (%ls) and its name exceed buffer size (%d).\n", root_directory, PYI_PATH_MAX);
    } else {
        struct _stat statbuf;
        if (_wstat(dll_fullpath, &statbuf) == 0) {
            PYI_DEBUG_W(L"DYLIB: attempting to pre-load bundled copy of ucrtbase.dll: %ls\n", dll_fullpath);
            LoadLibraryExW(dll_fullpath, NULL, LOAD_WITH_ALTERED_SEARCH_PATH);
        }
    }

    /* Look for python shared library relative to the top-level application directory.
     * Assuming that python shared library name contains only ASCII characters,
     * we can use it directly in the wide-char string formatting function,
     * without having to explicitly convert it from UTF8 to wide-char. */
    if (swprintf(dll_fullpath, PYI_PATH_MAX, L"%ls\\%hs", root_directory, python_libname) >= PYI_PATH_MAX) {
        PYI_ERROR_W(L"Path of Python DLL (%ls) and its name (%hs) exceed buffer size (%d).\n", root_directory, python_libname, PYI_PATH_MAX);
        return -1;
    }

    PYI_DEBUG_W(L"DYLIB: loading Python DLL: %ls\n", dll_fullpath);

    dylib->handle = LoadLibraryExW(dll_fullpath, NULL, LOAD_WITH_ALTERED_SEARCH_PATH);
    if (dylib->handle == NULL) {
        PYI_WINERROR_W(L"LoadLibrary", L"Failed to load Python DLL '%ls'.\n", dll_fullpath);
        return -1;
    }

    return 0;
}

#else

static int _pyi_dylib_python_load_library(
    struct DYLIB_PYTHON *dylib,
    const char *root_directory,
    const char *python_libname
)
{
#ifdef AIX
    /* On AIX, if we are trying to load a shared object in an .a archive
     * (e.g., `/path/to/libpython3.9.a(libpython3.9.so)`), we need to
     * set `RTLD_MEMBER` flag. It seems that we can use this flag with
     * regular shared library (.so) files as well, so we can get away
     * with having it always set (otherwise, we would need to check
     * whether the passed filename ends with ')' or not). For RTLD_MEMBER
     * to be defined, the program needs to be compiled with _ALL_SOURCE
     * defined, which is done globally in the `waf` build script. */
    const int dlopen_flags = RTLD_NOW | RTLD_GLOBAL | RTLD_MEMBER;
#else
    const int dlopen_flags = RTLD_NOW | RTLD_GLOBAL;
#endif

    char dll_fullpath[PYI_PATH_MAX];

    /* Look for python shared library relative to the top-level application directory. */
    if (snprintf(dll_fullpath, PYI_PATH_MAX, "%s/%s", root_directory, python_libname) >= PYI_PATH_MAX) {
        PYI_ERROR("Path of Python shared library (%s) and its name (%s) exceed buffer size (%d).\n", root_directory, python_libname, PYI_PATH_MAX);
        return -1;
    }

    PYI_DEBUG("DYLIB: loading Python shared library: %s\n", dll_fullpath);

    /* Load the shared library */
    dylib->handle = dlopen(dll_fullpath, dlopen_flags);
    if (dylib->handle == NULL) {
        PYI_ERROR("Failed to load Python shared library '%s': %s\n", dll_fullpath, dlerror());
        return -1;
    }

    return 0;
}

#endif /* defined(_WIN32) */


/* Import symbols from the loaded shared library */
static int _pyi_dylib_python_import_symbols(struct DYLIB_PYTHON *dylib)
{
    /* Extend PYI_EXT_FUNC_BIND() with error handling. */
#ifdef _WIN32
    /* Function names always contain ASCII characters, so we can safely
     * format ANSI string (obtained via stringification) into wide-char
     * message string. */
    #define _IMPORT_FUNCTION(name) \
        PYI_EXT_FUNC_BIND(dylib->handle, name, dylib->name); \
        if (!dylib->name) { \
            PYI_WINERROR_W(L"GetProcAddress", L"Failed to import symbol %hs from Python DLL.\n", #name); \
            return -1; \
        }
#else
    /* Extend PYI_EXT_FUNC_BIND() with error handling. */
    #define _IMPORT_FUNCTION(name) \
        PYI_EXT_FUNC_BIND(dylib->handle, name, dylib->name); \
        if (!dylib->name) { \
            PYI_ERROR("Failed to import symbol %s from Python shared library: %s\n", #name, dlerror()); \
            return -1; \
        }
#endif

    _IMPORT_FUNCTION(Py_DecRef)
    _IMPORT_FUNCTION(Py_DecodeLocale)
    _IMPORT_FUNCTION(Py_ExitStatusException)
    _IMPORT_FUNCTION(Py_Finalize)
    _IMPORT_FUNCTION(Py_InitializeFromConfig)
    _IMPORT_FUNCTION(Py_IsInitialized)
    _IMPORT_FUNCTION(Py_PreInitialize)

    _IMPORT_FUNCTION(PyConfig_Clear)
    _IMPORT_FUNCTION(PyConfig_InitIsolatedConfig)
    _IMPORT_FUNCTION(PyConfig_Read)
    _IMPORT_FUNCTION(PyConfig_SetBytesString)
    _IMPORT_FUNCTION(PyConfig_SetString)
    _IMPORT_FUNCTION(PyConfig_SetWideStringList)

    _IMPORT_FUNCTION(PyErr_Clear)
    _IMPORT_FUNCTION(PyErr_Fetch)
    _IMPORT_FUNCTION(PyErr_NormalizeException)
    _IMPORT_FUNCTION(PyErr_Occurred)
    _IMPORT_FUNCTION(PyErr_Print)
    _IMPORT_FUNCTION(PyErr_Restore)

    _IMPORT_FUNCTION(PyEval_EvalCode)

    _IMPORT_FUNCTION(PyImport_AddModule)
    _IMPORT_FUNCTION(PyImport_ExecCodeModule)
    _IMPORT_FUNCTION(PyImport_ImportModule)

    _IMPORT_FUNCTION(PyList_Append)

    _IMPORT_FUNCTION(PyMarshal_ReadObjectFromString)

    _IMPORT_FUNCTION(PyMem_RawFree)

    _IMPORT_FUNCTION(PyModule_GetDict)

    _IMPORT_FUNCTION(PyObject_CallFunction)
    _IMPORT_FUNCTION(PyObject_CallFunctionObjArgs)
    _IMPORT_FUNCTION(PyObject_GetAttrString)
    _IMPORT_FUNCTION(PyObject_SetAttrString)
    _IMPORT_FUNCTION(PyObject_Str)

    _IMPORT_FUNCTION(PyPreConfig_InitIsolatedConfig)

    _IMPORT_FUNCTION(PyRun_SimpleStringFlags)

    _IMPORT_FUNCTION(PyStatus_Exception)

    _IMPORT_FUNCTION(PySys_GetObject)
    _IMPORT_FUNCTION(PySys_SetObject)

    _IMPORT_FUNCTION(PyUnicode_AsUTF8)
    _IMPORT_FUNCTION(PyUnicode_Decode)
    _IMPORT_FUNCTION(PyUnicode_DecodeFSDefault)
    _IMPORT_FUNCTION(PyUnicode_FromFormat)
    _IMPORT_FUNCTION(PyUnicode_FromString)
    _IMPORT_FUNCTION(PyUnicode_Join)
    _IMPORT_FUNCTION(PyUnicode_Replace)

#undef _IMPORT_FUNCTION

    return 0;
}


/* The API functions */
struct DYLIB_PYTHON *pyi_dylib_python_load(const char *root_directory, const char *python_libname, int python_version)
{
    struct DYLIB_PYTHON *dylib;
    int ret;

    /* Allocate structure */
    dylib = (struct DYLIB_PYTHON *)calloc(1, sizeof(struct DYLIB_PYTHON));
    if (dylib == NULL) {
        PYI_PERROR("calloc", "Could not allocate memory for DYLIB_PYTHON structure.\n");
        return NULL;
    }

    /* Store version info */
    dylib->version = python_version;

    /* Load shared library */
    ret = _pyi_dylib_python_load_library(dylib, root_directory, python_libname);
    if (ret != 0) {
        goto cleanup;
    }
    PYI_DEBUG("DYLIB: loaded Python shared library.\n");

    /* Import functions/symbols */
    ret = _pyi_dylib_python_import_symbols(dylib);
    if (ret != 0) {
        goto cleanup;
    }
    PYI_DEBUG("DYLIB: imported symbols from Python shared library.\n");

    return dylib;

cleanup:
    pyi_dylib_python_cleanup(&dylib);
    return dylib;
}

void pyi_dylib_python_cleanup(struct DYLIB_PYTHON **dylib_ref)
{
    struct DYLIB_PYTHON *dylib = *dylib_ref;

    *dylib_ref = NULL;

    if (dylib == NULL) {
        return;
    }

    /* Unload the shared library */
    if (dylib->handle != NULL) {
        PYI_DEBUG("DYLIB: unloading Python shared library...\n");

#ifdef _WIN32
        if (FreeLibrary(dylib->handle) == 0) {
#else
        if (dlclose(dylib->handle) < 0) {
#endif
            PYI_DEBUG("DYLIB: failed to unload Python shared library!\n");
        } else {
            PYI_DEBUG("DYLIB: unloaded Python shared library.\n");
        }
    }

    /* Free the allocated structure */
    free(dylib);
}
