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
 * Dynamic bindings of Tcl and Tk shared libraries (the subset of API
 * used by splash screen). This header effectively replaces tcl.h and tk.h
 * headers.
 */

#ifndef PYI_DYLIB_TCLTK_H
#define PYI_DYLIB_TCLTK_H

#ifdef _WIN32
    #include <windows.h>
#endif

#include "pyi_global.h"

/* Macros defined in Tcl and copied over for easier understanding of the code */
#define TCL_OK 0
#define TCL_ERROR 1

#define TCL_GLOBAL_ONLY 1

#define TCL_THREAD_NOFLAGS 0
#define TCL_THREAD_JOINABLE 1

/* Opaque Tcl/Tk types */
typedef struct Tcl_Interp_ Tcl_Interp;
typedef struct Tcl_ThreadId_ *Tcl_ThreadId;
typedef struct Tcl_Command_ *Tcl_Command;
typedef struct Tcl_Event Tcl_Event;
typedef struct Tcl_Obj_ Tcl_Obj;
typedef struct Tcl_Condition_ *Tcl_Condition;
typedef struct Tcl_Mutex_ *Tcl_Mutex;
typedef struct Tcl_Time_ Tcl_Time;
typedef void *ClientData;

/* Function prototypes */
typedef int (Tcl_ObjCmdProc)(ClientData, Tcl_Interp *, int, Tcl_Obj *const[]);
typedef int (Tcl_CmdDeleteProc)(ClientData);
typedef int (Tcl_EventProc)(Tcl_Event *, int);

#ifdef _WIN32
    typedef unsigned (__stdcall Tcl_ThreadCreateProc)(ClientData clientData);
    #define Tcl_ThreadCreateType unsigned __stdcall
    #define TCL_THREAD_CREATE_RETURN return 0
#else /* _WIN32 */
    typedef void (Tcl_ThreadCreateProc)(ClientData clientData);
    #define Tcl_ThreadCreateType void
    #define TCL_THREAD_CREATE_RETURN
#endif /* _WIN32 */

/* Struct describing a Tcl event. This has been copied from tcl.h
 * It is probably safe to just copy this, since this struct has not been
 * changed since 1998 */
struct Tcl_Event
{
    Tcl_EventProc *proc; /* Function to call to service this event. */
    struct Tcl_Event *nextPtr; /* Next in list of pending events, or NULL. */
};

typedef enum
{
    TCL_QUEUE_TAIL,
    TCL_QUEUE_HEAD,
    TCL_QUEUE_MARK
} Tcl_QueuePosition;


/*
 * Tcl shared library and bound functions imported from it.
 */

/* Tcl Initialization/Destruction */
PYI_EXT_FUNC_PROTO(int, Tcl_Init, (Tcl_Interp *))
PYI_EXT_FUNC_PROTO(Tcl_Interp*, Tcl_CreateInterp, (void))
PYI_EXT_FUNC_PROTO(void, Tcl_FindExecutable, (const char *))
PYI_EXT_FUNC_PROTO(int, Tcl_DoOneEvent, (int))
PYI_EXT_FUNC_PROTO(void, Tcl_Finalize, (void))
PYI_EXT_FUNC_PROTO(void, Tcl_FinalizeThread, (void))
PYI_EXT_FUNC_PROTO(void, Tcl_DeleteInterp, (Tcl_Interp *))

/* Threading */
PYI_EXT_FUNC_PROTO(int, Tcl_CreateThread, (Tcl_ThreadId *, Tcl_ThreadCreateProc *, ClientData, int, int))
PYI_EXT_FUNC_PROTO(Tcl_ThreadId, Tcl_GetCurrentThread, (void))
PYI_EXT_FUNC_PROTO(int, Tcl_JoinThread, (Tcl_ThreadId, int *))
PYI_EXT_FUNC_PROTO(void, Tcl_MutexLock, (Tcl_Mutex *))
PYI_EXT_FUNC_PROTO(void, Tcl_MutexUnlock, (Tcl_Mutex *))
PYI_EXT_FUNC_PROTO(void, Tcl_MutexFinalize, (Tcl_Mutex *))
PYI_EXT_FUNC_PROTO(void, Tcl_ConditionFinalize, (Tcl_Condition *))
PYI_EXT_FUNC_PROTO(void, Tcl_ConditionNotify, (Tcl_Condition *))
PYI_EXT_FUNC_PROTO(void, Tcl_ConditionWait, (Tcl_Condition *, Tcl_Mutex *, const Tcl_Time *))
PYI_EXT_FUNC_PROTO(void, Tcl_ThreadQueueEvent, (Tcl_ThreadId, Tcl_Event *, Tcl_QueuePosition))
PYI_EXT_FUNC_PROTO(void, Tcl_ThreadAlert, (Tcl_ThreadId threadId))

/* Tcl interpreter manipulation */
PYI_EXT_FUNC_PROTO(const char*, Tcl_GetVar2, (Tcl_Interp *, const char *, const char *, int))
PYI_EXT_FUNC_PROTO(const char*, Tcl_SetVar2, (Tcl_Interp *, const char *, const char *, const char *, int))
PYI_EXT_FUNC_PROTO(Tcl_Command, Tcl_CreateObjCommand, (Tcl_Interp *, const char *, Tcl_ObjCmdProc *, ClientData, Tcl_CmdDeleteProc *))
PYI_EXT_FUNC_PROTO(char *, Tcl_GetString, (Tcl_Obj *))
PYI_EXT_FUNC_PROTO(Tcl_Obj *, Tcl_NewStringObj, (const char *, int))
PYI_EXT_FUNC_PROTO(Tcl_Obj *, Tcl_NewByteArrayObj, (const unsigned char *, int))
PYI_EXT_FUNC_PROTO(Tcl_Obj *, Tcl_SetVar2Ex, (Tcl_Interp *, const char *, const char *, Tcl_Obj *, int))
PYI_EXT_FUNC_PROTO(Tcl_Obj *, Tcl_GetObjResult, (Tcl_Interp *))

/* Evaluating scripts and memory functions */
PYI_EXT_FUNC_PROTO(int, Tcl_EvalFile, (Tcl_Interp *, const char *))
PYI_EXT_FUNC_PROTO(int, Tcl_EvalEx, (Tcl_Interp *, const char *, int, int))
PYI_EXT_FUNC_PROTO(int, Tcl_EvalObjv, (Tcl_Interp *, int, Tcl_Obj * const[], int))
PYI_EXT_FUNC_PROTO(char *, Tcl_Alloc, (unsigned int))
PYI_EXT_FUNC_PROTO(void, Tcl_Free, (char *))

/* Tk functions */
PYI_EXT_FUNC_PROTO(int, Tk_Init, (Tcl_Interp *))
PYI_EXT_FUNC_PROTO(int, Tk_GetNumMainWindows, (void))

/* The actual function-pointer structure */
struct DYLIB_TCLTK
{
    /* Shared library handles */
    pyi_dylib_t handle_tcl;
    pyi_dylib_t handle_tk;

    /* Function pointers for imported functions: Tcl */
    PYI_EXT_FUNC_ENTRY(Tcl_Init)
    PYI_EXT_FUNC_ENTRY(Tcl_CreateInterp)
    PYI_EXT_FUNC_ENTRY(Tcl_FindExecutable)
    PYI_EXT_FUNC_ENTRY(Tcl_DoOneEvent)
    PYI_EXT_FUNC_ENTRY(Tcl_Finalize)
    PYI_EXT_FUNC_ENTRY(Tcl_FinalizeThread)
    PYI_EXT_FUNC_ENTRY(Tcl_DeleteInterp)

    PYI_EXT_FUNC_ENTRY(Tcl_CreateThread)
    PYI_EXT_FUNC_ENTRY(Tcl_GetCurrentThread)
    PYI_EXT_FUNC_ENTRY(Tcl_JoinThread)
    PYI_EXT_FUNC_ENTRY(Tcl_MutexLock)
    PYI_EXT_FUNC_ENTRY(Tcl_MutexUnlock)
    PYI_EXT_FUNC_ENTRY(Tcl_MutexFinalize)
    PYI_EXT_FUNC_ENTRY(Tcl_ConditionFinalize)
    PYI_EXT_FUNC_ENTRY(Tcl_ConditionNotify)
    PYI_EXT_FUNC_ENTRY(Tcl_ConditionWait)
    PYI_EXT_FUNC_ENTRY(Tcl_ThreadQueueEvent)
    PYI_EXT_FUNC_ENTRY(Tcl_ThreadAlert)

    PYI_EXT_FUNC_ENTRY(Tcl_GetVar2)
    PYI_EXT_FUNC_ENTRY(Tcl_SetVar2)
    PYI_EXT_FUNC_ENTRY(Tcl_CreateObjCommand)
    PYI_EXT_FUNC_ENTRY(Tcl_GetString)
    PYI_EXT_FUNC_ENTRY(Tcl_NewStringObj)
    PYI_EXT_FUNC_ENTRY(Tcl_NewByteArrayObj)
    PYI_EXT_FUNC_ENTRY(Tcl_SetVar2Ex)
    PYI_EXT_FUNC_ENTRY(Tcl_GetObjResult)

    PYI_EXT_FUNC_ENTRY(Tcl_EvalFile)
    PYI_EXT_FUNC_ENTRY(Tcl_EvalEx)
    PYI_EXT_FUNC_ENTRY(Tcl_EvalObjv)
    PYI_EXT_FUNC_ENTRY(Tcl_Alloc)
    PYI_EXT_FUNC_ENTRY(Tcl_Free)

    /* Function pointers for imported functions: Tk */
    PYI_EXT_FUNC_ENTRY(Tk_Init)
    PYI_EXT_FUNC_ENTRY(Tk_GetNumMainWindows)
};

struct DYLIB_TCLTK *pyi_dylib_tcltk_load(const char *tcl_fullpath, const char *tk_fullpath);
void pyi_dylib_tcltk_cleanup(struct DYLIB_TCLTK **dylib_ref);

#endif /* PYI_DYLIB_TCLTK_H */
