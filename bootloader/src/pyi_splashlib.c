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
 * tcl.h and tk.h replacement
 */

#ifdef _WIN32
    #include <windows.h>  /* HMODULE */
#else
    #include <dlfcn.h>  /* dlsym */
#endif
#include <stddef.h>

/* PyInstaller headers */
#include "pyi_global.h"
#include "pyi_splashlib.h"

/* Tcl Initialization/Destruction */
DECLPROC(Tcl_Init);
DECLPROC(Tcl_CreateInterp);
DECLPROC(Tcl_FindExecutable);
DECLPROC(Tcl_DoOneEvent);
DECLPROC(Tcl_Finalize);
DECLPROC(Tcl_FinalizeThread);
DECLPROC(Tcl_DeleteInterp);

/* Threading */
DECLPROC(Tcl_CreateThread);
DECLPROC(Tcl_GetCurrentThread);
DECLPROC(Tcl_MutexLock);
DECLPROC(Tcl_MutexUnlock);
DECLPROC(Tcl_ConditionFinalize);
DECLPROC(Tcl_ConditionNotify);
DECLPROC(Tcl_ConditionWait);
DECLPROC(Tcl_ThreadQueueEvent);
DECLPROC(Tcl_ThreadAlert);

/* Tcl interpreter manipulation */
DECLPROC(Tcl_GetVar2);
DECLPROC(Tcl_SetVar2);
DECLPROC(Tcl_CreateObjCommand);
DECLPROC(Tcl_GetString);
DECLPROC(Tcl_NewStringObj);
DECLPROC(Tcl_NewByteArrayObj);
DECLPROC(Tcl_SetVar2Ex);
DECLPROC(Tcl_GetObjResult);

/* Evaluating scripts and memory functions */
DECLPROC(Tcl_EvalFile);
DECLPROC(Tcl_EvalEx);
DECLPROC(Tcl_EvalObjv);
DECLPROC(Tcl_Alloc);
DECLPROC(Tcl_Free);

/* Tk */
DECLPROC(Tk_Init);
DECLPROC(Tk_GetNumMainWindows);

/*
 * Fill foreign function pointers with the valid dll functions.
 * This function will return 0 on success, a nonzero value
 * on failure
 */
int
pyi_splashlib_attach(dylib_t dll_tcl, dylib_t dll_tk)
{
    /* Tcl Initialization/Destruction */
    GETPROC(dll_tcl, Tcl_Init);
    GETPROC(dll_tcl, Tcl_CreateInterp);
    GETPROC(dll_tcl, Tcl_FindExecutable);
    GETPROC(dll_tcl, Tcl_DoOneEvent);
    GETPROC(dll_tcl, Tcl_Finalize);
    GETPROC(dll_tcl, Tcl_FinalizeThread);
    GETPROC(dll_tcl, Tcl_DeleteInterp);

    /* Threading */
    GETPROC(dll_tcl, Tcl_CreateThread);
    GETPROC(dll_tcl, Tcl_GetCurrentThread);
    GETPROC(dll_tcl, Tcl_MutexLock);
    GETPROC(dll_tcl, Tcl_MutexUnlock);
    GETPROC(dll_tcl, Tcl_ConditionFinalize);
    GETPROC(dll_tcl, Tcl_ConditionNotify);
    GETPROC(dll_tcl, Tcl_ConditionWait);
    GETPROC(dll_tcl, Tcl_ThreadQueueEvent);
    GETPROC(dll_tcl, Tcl_ThreadAlert);

    /* Tcl interpreter manipulation */
    GETPROC(dll_tcl, Tcl_GetVar2);
    GETPROC(dll_tcl, Tcl_SetVar2);
    GETPROC(dll_tcl, Tcl_CreateObjCommand);
    GETPROC(dll_tcl, Tcl_GetString);
    GETPROC(dll_tcl, Tcl_NewStringObj);
    GETPROC(dll_tcl, Tcl_NewByteArrayObj);
    GETPROC(dll_tcl, Tcl_SetVar2Ex);
    GETPROC(dll_tcl, Tcl_GetObjResult);

    /* Evaluating scripts and memory functions */
    GETPROC(dll_tcl, Tcl_EvalFile);
    GETPROC(dll_tcl, Tcl_EvalEx);
    GETPROC(dll_tcl, Tcl_EvalObjv);
    GETPROC(dll_tcl, Tcl_Alloc);
    GETPROC(dll_tcl, Tcl_Free);

    /* Tk */
    GETPROC(dll_tk, Tk_Init);
    GETPROC(dll_tk, Tk_GetNumMainWindows);

    VS("LOADER: Loaded functions from tcl/tk libraries.\n");
    return 0;
}
