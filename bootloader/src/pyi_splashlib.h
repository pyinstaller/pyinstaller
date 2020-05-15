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

#ifndef PYI_SPLASHLIB_H
#define PYI_SPLASHLIB_H

#ifdef _WIN32
    #include <windows.h>
#endif

#include "pyi_global.h"

/* Macros defined in TCL and copied over for easier understanding
 * of the code */
#define TCL_OK 0
#define TCL_ERROR 1

#define TCL_GLOBAL_ONLY      1

/* Opaque Tcl/Tk types */
typedef struct Tcl_Interp_ Tcl_Interp;
typedef struct Tcl_ThreadId_ *Tcl_ThreadId;
typedef struct Tcl_Command_ *Tcl_Command;
typedef struct Tcl_Event Tcl_Event;
typedef struct Tcl_Obj_ Tcl_Obj;
typedef struct Tcl_Condition_ *Tcl_Condition;
typedef struct Tcl_Mutex_ *Tcl_Mutex;
typedef struct Tcl_Time_ Tcl_Time;
typedef void* ClientData;

/* Function prototypes */
typedef int (Tcl_ObjCmdProc)(ClientData, Tcl_Interp *, int, Tcl_Obj *const[]);
typedef int (Tcl_CmdDeleteProc)(ClientData);
typedef int (Tcl_EventProc) (Tcl_Event *, int);
#ifdef _WIN32
typedef unsigned (__stdcall Tcl_ThreadCreateProc)(ClientData clientData);
    #define Tcl_ThreadCreateType        unsigned __stdcall
    #define TCL_THREAD_CREATE_RETURN    return 0
#else
typedef void (Tcl_ThreadCreateProc) (ClientData clientData);
    #define Tcl_ThreadCreateType        void
    #define TCL_THREAD_CREATE_RETURN
#endif

/* Struct describing a tcl event. This has been copied from tcl.h
 * It is probably safe to just copy this, since this struct hasn't been
 * changed since 1998 */
struct Tcl_Event {
    Tcl_EventProc *   proc;    /* Function to call to service this event. */
    struct Tcl_Event *nextPtr; /* Next in list of pending events, or NULL. */
};

typedef enum {
    TCL_QUEUE_TAIL, TCL_QUEUE_HEAD, TCL_QUEUE_MARK
} Tcl_QueuePosition;

/**
 * Foreign functions from tcl/tk
 */
/* Tcl Initialization/Destruction */
EXTDECLPROC(int, Tcl_Init, (Tcl_Interp *));
EXTDECLPROC(Tcl_Interp*, Tcl_CreateInterp, (void));
EXTDECLPROC(void, Tcl_FindExecutable, (const char *));
EXTDECLPROC(int, Tcl_DoOneEvent, (int));
EXTDECLPROC(void, Tcl_Finalize, (void));
EXTDECLPROC(void, Tcl_FinalizeThread, (void));
EXTDECLPROC(void, Tcl_DeleteInterp, (Tcl_Interp *));

/* Threading */
EXTDECLPROC(int, Tcl_CreateThread,
            (Tcl_ThreadId *, Tcl_ThreadCreateProc *, ClientData, int, int));
EXTDECLPROC(Tcl_ThreadId, Tcl_GetCurrentThread, (void));
EXTDECLPROC(void, Tcl_MutexLock, (Tcl_Mutex * ));
EXTDECLPROC(void, Tcl_MutexUnlock, (Tcl_Mutex * ));
EXTDECLPROC(void, Tcl_ConditionFinalize, (Tcl_Condition *));
EXTDECLPROC(void, Tcl_ConditionNotify, (Tcl_Condition *));
EXTDECLPROC(void, Tcl_ConditionWait, (Tcl_Condition *, Tcl_Mutex *, const Tcl_Time *));
EXTDECLPROC(void, Tcl_ThreadQueueEvent, (Tcl_ThreadId, Tcl_Event *, Tcl_QueuePosition));
EXTDECLPROC(void, Tcl_ThreadAlert, (Tcl_ThreadId threadId));

/* Tcl interpreter manipulation */
EXTDECLPROC(const char*, Tcl_GetVar2, (Tcl_Interp *, const char *, const char *, int));
EXTDECLPROC(const char*, Tcl_SetVar2,
            (Tcl_Interp *, const char *, const char *, const char *, int));
EXTDECLPROC(Tcl_Command, Tcl_CreateObjCommand,
            (Tcl_Interp *, const char *, Tcl_ObjCmdProc *, ClientData,
             Tcl_CmdDeleteProc *));
EXTDECLPROC(char*, Tcl_GetString, (Tcl_Obj *));
EXTDECLPROC(Tcl_Obj*, Tcl_NewStringObj, (const char *, int));
EXTDECLPROC(Tcl_Obj*, Tcl_NewByteArrayObj, (const unsigned char *, int));
EXTDECLPROC(Tcl_Obj*, Tcl_SetVar2Ex,
            (Tcl_Interp *, const char *, const char *, Tcl_Obj *, int));
EXTDECLPROC(Tcl_Obj*, Tcl_GetObjResult, (Tcl_Interp *));

/* Evaluating scripts and memory functions */
EXTDECLPROC(int, Tcl_EvalFile, (Tcl_Interp *, const char *));
EXTDECLPROC(int, Tcl_EvalEx, (Tcl_Interp *, const char *, int, int));
EXTDECLPROC(int, Tcl_EvalObjv, (Tcl_Interp *, int, Tcl_Obj * const[], int));
EXTDECLPROC(char*, Tcl_Alloc, (unsigned int));
EXTDECLPROC(void, Tcl_Free, (char *));

/* Tk */
EXTDECLPROC(int, Tk_Init, (Tcl_Interp *));
EXTDECLPROC(int, Tk_GetNumMainWindows, (void));

int pyi_splashlib_attach(dylib_t dll_tcl, dylib_t dll_tk);

#endif  /*PYI_SPLASHLIB_H */
