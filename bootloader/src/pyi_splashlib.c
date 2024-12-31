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
PYI_DECLPROC(Tcl_Init)
PYI_DECLPROC(Tcl_CreateInterp)
PYI_DECLPROC(Tcl_FindExecutable)
PYI_DECLPROC(Tcl_DoOneEvent)
PYI_DECLPROC(Tcl_Finalize)
PYI_DECLPROC(Tcl_FinalizeThread)
PYI_DECLPROC(Tcl_DeleteInterp)

/* Threading */
PYI_DECLPROC(Tcl_CreateThread)
PYI_DECLPROC(Tcl_GetCurrentThread)
PYI_DECLPROC(Tcl_JoinThread)
PYI_DECLPROC(Tcl_MutexLock)
PYI_DECLPROC(Tcl_MutexUnlock)
PYI_DECLPROC(Tcl_MutexFinalize)
PYI_DECLPROC(Tcl_ConditionFinalize)
PYI_DECLPROC(Tcl_ConditionNotify)
PYI_DECLPROC(Tcl_ConditionWait)
PYI_DECLPROC(Tcl_ThreadQueueEvent)
PYI_DECLPROC(Tcl_ThreadAlert)

/* Tcl interpreter manipulation */
PYI_DECLPROC(Tcl_GetVar2)
PYI_DECLPROC(Tcl_SetVar2)
PYI_DECLPROC(Tcl_CreateObjCommand)
PYI_DECLPROC(Tcl_GetString)
PYI_DECLPROC(Tcl_NewStringObj)
PYI_DECLPROC(Tcl_NewByteArrayObj)
PYI_DECLPROC(Tcl_SetVar2Ex)
PYI_DECLPROC(Tcl_GetObjResult)

/* Evaluating scripts and memory functions */
PYI_DECLPROC(Tcl_EvalFile)
PYI_DECLPROC(Tcl_EvalEx)
PYI_DECLPROC(Tcl_EvalObjv)
PYI_DECLPROC(Tcl_Alloc)
PYI_DECLPROC(Tcl_Free)

/* Tk */
PYI_DECLPROC(Tk_Init)
PYI_DECLPROC(Tk_GetNumMainWindows)


/*
 * Bind all required functions from Tcl/Tk shared libraries.
 */
int
pyi_splashlib_bind_functions(pyi_dylib_t dll_tcl, pyi_dylib_t dll_tk)
{
    /* Tcl Initialization/Destruction */
    PYI_GETPROC(dll_tcl, Tcl_Init)
    PYI_GETPROC(dll_tcl, Tcl_CreateInterp)
    PYI_GETPROC(dll_tcl, Tcl_FindExecutable)
    PYI_GETPROC(dll_tcl, Tcl_DoOneEvent)
    PYI_GETPROC(dll_tcl, Tcl_Finalize)
    PYI_GETPROC(dll_tcl, Tcl_FinalizeThread)
    PYI_GETPROC(dll_tcl, Tcl_DeleteInterp)

    /* Threading */
    PYI_GETPROC(dll_tcl, Tcl_CreateThread)
    PYI_GETPROC(dll_tcl, Tcl_GetCurrentThread)
    PYI_GETPROC(dll_tcl, Tcl_JoinThread)
    PYI_GETPROC(dll_tcl, Tcl_MutexLock)
    PYI_GETPROC(dll_tcl, Tcl_MutexUnlock)
    PYI_GETPROC(dll_tcl, Tcl_MutexFinalize)
    PYI_GETPROC(dll_tcl, Tcl_ConditionFinalize)
    PYI_GETPROC(dll_tcl, Tcl_ConditionNotify)
    PYI_GETPROC(dll_tcl, Tcl_ConditionWait)
    PYI_GETPROC(dll_tcl, Tcl_ThreadQueueEvent)
    PYI_GETPROC(dll_tcl, Tcl_ThreadAlert)

    /* Tcl interpreter manipulation */
    PYI_GETPROC(dll_tcl, Tcl_GetVar2)
    PYI_GETPROC(dll_tcl, Tcl_SetVar2)
    PYI_GETPROC(dll_tcl, Tcl_CreateObjCommand)
    PYI_GETPROC(dll_tcl, Tcl_GetString)
    PYI_GETPROC(dll_tcl, Tcl_NewStringObj)
    PYI_GETPROC(dll_tcl, Tcl_NewByteArrayObj)
    PYI_GETPROC(dll_tcl, Tcl_SetVar2Ex)
    PYI_GETPROC(dll_tcl, Tcl_GetObjResult)

    /* Evaluating scripts and memory functions */
    PYI_GETPROC(dll_tcl, Tcl_EvalFile)
    PYI_GETPROC(dll_tcl, Tcl_EvalEx)
    PYI_GETPROC(dll_tcl, Tcl_EvalObjv)
    PYI_GETPROC(dll_tcl, Tcl_Alloc)
    PYI_GETPROC(dll_tcl, Tcl_Free)

    /* Tk */
    PYI_GETPROC(dll_tk, Tk_Init)
    PYI_GETPROC(dll_tk, Tk_GetNumMainWindows)

    PYI_DEBUG("LOADER: loaded functions from Tcl/Tk shared libraries.\n");
    return 0;
}
