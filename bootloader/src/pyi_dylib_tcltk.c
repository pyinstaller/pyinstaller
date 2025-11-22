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
#include "pyi_dylib_tcltk.h"
#include "pyi_utils.h"


#if defined(_WIN32)

static int _pyi_dylib_tcltk_load_libraries(struct DYLIB_TCLTK *dylib, const char *tcl_fullpath_utf8, const char *tk_fullpath_utf8)
{
    wchar_t dll_fullpath[PYI_PATH_MAX];

    /* Tcl shared library */
    if (pyi_win32_utf8_to_wcs(tcl_fullpath_utf8, dll_fullpath, PYI_PATH_MAX) == NULL) {
        PYI_ERROR_W(L"Failed to convert path to Tcl DLL to wide-char string.\n");
        return -1;
    }

    PYI_DEBUG_W(L"DYLIB: loading Tcl DLL: %ls\n", dll_fullpath);

    dylib->handle_tcl = LoadLibraryExW(dll_fullpath, NULL, LOAD_WITH_ALTERED_SEARCH_PATH);
    if (dylib->handle_tcl == NULL) {
        PYI_WINERROR_W(L"LoadLibrary", L"Failed to load Tcl DLL '%ls'.\n", dll_fullpath);
        return -1;
    }

    /* Tk shared library */
    if (pyi_win32_utf8_to_wcs(tk_fullpath_utf8, dll_fullpath, PYI_PATH_MAX) == NULL) {
        PYI_ERROR_W(L"Failed to convert path to Tk DLL to wide-char string\n");
        return -1;
    }

    PYI_DEBUG_W(L"DYLIB: loading Tk DLL: %ls\n", dll_fullpath);

    dylib->handle_tk = LoadLibraryExW(dll_fullpath, NULL, LOAD_WITH_ALTERED_SEARCH_PATH);
    if (dylib->handle_tk == NULL) {
        PYI_WINERROR_W(L"LoadLibrary", L"Failed to load Tk DLL '%ls'.\n", dll_fullpath);
        return -1;
    }

    return 0;
}


#else

static int _pyi_dylib_tcltk_load_libraries(struct DYLIB_TCLTK *dylib, const char *tcl_fullpath, const char *tk_fullpath)
{
#ifdef AIX
    /* See comment in _pyi_dylib_python_load_library(). */
    const int dlopen_flags = RTLD_NOW | RTLD_GLOBAL | RTLD_MEMBER;
#else
    const int dlopen_flags = RTLD_NOW | RTLD_GLOBAL;
#endif

    /* Tcl shared library */
    PYI_DEBUG("DYLIB: loading Tcl shared library: %s\n", tcl_fullpath);

    dylib->handle_tcl = dlopen(tcl_fullpath, dlopen_flags);
    if (dylib->handle_tcl == NULL) {
        PYI_ERROR("Failed to load Tcl shared library '%s': %s\n", tcl_fullpath, dlerror());
        return -1;
    }

    /* Tk shared library */
    PYI_DEBUG("DYLIB: loading Tk shared library: %s\n", tk_fullpath);

    dylib->handle_tk = dlopen(tk_fullpath, dlopen_flags);
    if (dylib->handle_tk == NULL) {
        PYI_ERROR("Failed to load Tk shared library '%s': %s\n", tk_fullpath, dlerror());
        return -1;
    }

    return 0;
}

#endif


/* Import symbols from the loaded shared library */
static int _pyi_dylib_tcltk_import_tcl_symbols(struct DYLIB_TCLTK *dylib)
{
    /* Extend PYI_EXT_FUNC_BIND() with error handling. */
#ifdef _WIN32
    /* Function names always contain ASCII characters, so we can safely
     * format ANSI string (obtained via stringification) into wide-char
     * message string. */
    #define _IMPORT_FUNCTION_EX(name, dest_name) \
        PYI_EXT_FUNC_BIND_EX(dylib->handle_tcl, dest_name, name, dylib->dest_name); \
        if (!dylib->dest_name) { \
            PYI_WINERROR_W(L"GetProcAddress", L"Failed to import symbol %hs from Tcl DLL.\n", #name); \
            return -1; \
        }
#else
    /* Extend PYI_EXT_FUNC_BIND() with error handling. */
    #define _IMPORT_FUNCTION_EX(name, dest_name) \
        PYI_EXT_FUNC_BIND_EX(dylib->handle_tcl, dest_name, name, dylib->dest_name); \
        if (!dylib->dest_name) { \
            PYI_ERROR("Failed to import symbol %s from Tcl shared library: %s\n", #name, dlerror()); \
            return -1; \
        }
#endif

    #define _IMPORT_FUNCTION(name) _IMPORT_FUNCTION_EX(name, name)

    /* Bind the GetVersion function and query the major version of Tcl,
     * in order to determine whether we should bind functions to prototypes
     * with 64-bit arguments (Tcl >= 9.0) or 32-bit arguments (Tcl < 9.0). */
    _IMPORT_FUNCTION(Tcl_GetVersion)
    dylib->Tcl_GetVersion(&dylib->tcl_major, NULL, NULL, NULL);
    PYI_DEBUG("DYLIB: binding Tcl with major version %d.\n", dylib->tcl_major);

    _IMPORT_FUNCTION(Tcl_Init)
    _IMPORT_FUNCTION(Tcl_CreateInterp)
    _IMPORT_FUNCTION(Tcl_FindExecutable)
    _IMPORT_FUNCTION(Tcl_DoOneEvent)
    _IMPORT_FUNCTION(Tcl_Finalize)
    _IMPORT_FUNCTION(Tcl_FinalizeThread)
    _IMPORT_FUNCTION(Tcl_DeleteInterp)

    if (dylib->tcl_major >= 9) {
        _IMPORT_FUNCTION_EX(Tcl_CreateThread, Tcl_CreateThread_9)
    } else {
        _IMPORT_FUNCTION_EX(Tcl_CreateThread, Tcl_CreateThread_8)
    }
    _IMPORT_FUNCTION(Tcl_GetCurrentThread)
    _IMPORT_FUNCTION(Tcl_JoinThread)
    _IMPORT_FUNCTION(Tcl_MutexLock)
    _IMPORT_FUNCTION(Tcl_MutexUnlock)
    _IMPORT_FUNCTION(Tcl_MutexFinalize)
    _IMPORT_FUNCTION(Tcl_ConditionFinalize)
    _IMPORT_FUNCTION(Tcl_ConditionNotify)
    _IMPORT_FUNCTION(Tcl_ConditionWait)
    _IMPORT_FUNCTION(Tcl_ThreadQueueEvent)
    _IMPORT_FUNCTION(Tcl_ThreadAlert)

    _IMPORT_FUNCTION(Tcl_GetVar2)
    _IMPORT_FUNCTION(Tcl_SetVar2)
    _IMPORT_FUNCTION(Tcl_UnsetVar2)
    _IMPORT_FUNCTION(Tcl_CreateObjCommand)
    _IMPORT_FUNCTION(Tcl_GetString)
    if (dylib->tcl_major >= 9) {
        _IMPORT_FUNCTION_EX(Tcl_NewStringObj, Tcl_NewStringObj_9)
        _IMPORT_FUNCTION_EX(Tcl_NewByteArrayObj, Tcl_NewByteArrayObj_9)
    } else {
        _IMPORT_FUNCTION_EX(Tcl_NewStringObj, Tcl_NewStringObj_8)
        _IMPORT_FUNCTION_EX(Tcl_NewByteArrayObj, Tcl_NewByteArrayObj_8)
    }
    _IMPORT_FUNCTION(Tcl_SetVar2Ex)
    _IMPORT_FUNCTION(Tcl_GetObjResult)
    _IMPORT_FUNCTION(Tcl_SetObjResult)

    _IMPORT_FUNCTION(Tcl_EvalFile)
    if (dylib->tcl_major >= 9) {
        _IMPORT_FUNCTION_EX(Tcl_EvalEx, Tcl_EvalEx_9)
        _IMPORT_FUNCTION_EX(Tcl_EvalObjv, Tcl_EvalObjv_9)
        _IMPORT_FUNCTION_EX(Tcl_Alloc, Tcl_Alloc_9)
    } else {
        _IMPORT_FUNCTION_EX(Tcl_EvalEx, Tcl_EvalEx_8)
        _IMPORT_FUNCTION_EX(Tcl_EvalObjv, Tcl_EvalObjv_8)
        _IMPORT_FUNCTION_EX(Tcl_Alloc, Tcl_Alloc_8)
    }
    _IMPORT_FUNCTION(Tcl_Free)

#undef _IMPORT_FUNCTION
#undef _IMPORT_FUNCTION_EX

    return 0;
}

static int _pyi_dylib_tcltk_import_tk_symbols(struct DYLIB_TCLTK *dylib)
{
    /* Extend PYI_EXT_FUNC_BIND() with error handling. */
#ifdef _WIN32
    /* Function names always contain ASCII characters, so we can safely
     * format ANSI string (obtained via stringification) into wide-char
     * message string. */
    #define _IMPORT_FUNCTION(name) \
        PYI_EXT_FUNC_BIND(dylib->handle_tk, name, dylib->name); \
        if (!dylib->name) { \
            PYI_WINERROR_W(L"GetProcAddress", L"Failed to import symbol %hs from Tk DLL.\n", #name); \
            return -1; \
        }
#else
    /* Extend PYI_EXT_FUNC_BIND() with error handling. */
    #define _IMPORT_FUNCTION(name) \
        PYI_EXT_FUNC_BIND(dylib->handle_tk, name, dylib->name); \
        if (!dylib->name) { \
            PYI_ERROR("Failed to import symbol %s from Tk shared library: %s\n", #name, dlerror()); \
            return -1; \
        }
#endif

    _IMPORT_FUNCTION(Tk_Init)
    _IMPORT_FUNCTION(Tk_GetNumMainWindows)

#undef _IMPORT_FUNCTION

    return 0;
}


/* The API functions */
struct DYLIB_TCLTK *pyi_dylib_tcltk_load(const char *tcl_fullpath, const char *tk_fullpath)
{
    struct DYLIB_TCLTK *dylib;
    int ret;

    /* Allocate structure */
    dylib = (struct DYLIB_TCLTK *)calloc(1, sizeof(struct DYLIB_TCLTK));
    if (dylib == NULL) {
        PYI_PERROR("calloc", "Could not allocate memory for DYLIB_TCLTK structure.\n");
        return NULL;
    }

    /* Load shared libraries */
    ret = _pyi_dylib_tcltk_load_libraries(dylib, tcl_fullpath, tk_fullpath);
    if (ret != 0) {
        goto cleanup;
    }
    PYI_DEBUG("DYLIB: loaded Tcl/Tk shared libraries.\n");

    /* Import functions/symbols */
    ret = _pyi_dylib_tcltk_import_tcl_symbols(dylib);
    if (ret != 0) {
        goto cleanup;
    }
    ret = _pyi_dylib_tcltk_import_tk_symbols(dylib);
    if (ret != 0) {
        goto cleanup;
    }
    PYI_DEBUG("DYLIB: imported symbols from Tcl/Tk shared libraries.\n");

    return dylib;

cleanup:
    pyi_dylib_tcltk_cleanup(&dylib);
    return dylib;
}

void pyi_dylib_tcltk_cleanup(struct DYLIB_TCLTK **dylib_ref)
{
    struct DYLIB_TCLTK *dylib = *dylib_ref;

    *dylib_ref = NULL;

    if (dylib == NULL) {
        return;
    }

    /* Unload the Tk shared library */
    if (dylib->handle_tk != NULL) {
        PYI_DEBUG("DYLIB: unloading Tk shared library...\n");

#ifdef _WIN32
        if (FreeLibrary(dylib->handle_tk) == 0) {
#else
        if (dlclose(dylib->handle_tk) < 0) {
#endif
            PYI_DEBUG("DYLIB: failed to unload Tk shared library!\n");
        } else {
            PYI_DEBUG("DYLIB: unloaded Tk shared library.\n");
        }
    }

    /* Unload the Tcl shared library */
    if (dylib->handle_tcl != NULL) {
        PYI_DEBUG("DYLIB: unloading Tcl shared library...\n");

#ifdef _WIN32
        if (FreeLibrary(dylib->handle_tcl) == 0) {
#else
        if (dlclose(dylib->handle_tcl) < 0) {
#endif
            PYI_DEBUG("DYLIB: failed to unload Tcl shared library!\n");
        } else {
            PYI_DEBUG("DYLIB: unloaded Tcl shared library.\n");
        }
    }

    /* Free the allocated structure */
    free(dylib);
}
