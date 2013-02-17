/*
 * ****************************************************************************
 * Copyright (c) 2013, PyInstaller Development Team.
 * Distributed under the terms of the GNU General Public License with exception
 * for distributing bootloader.
 *
 * The full license is in the file COPYING.txt, distributed with this software.
 * ****************************************************************************
 */



// TODO move this code to file  pyi_win32.c.


#define _WIN32_WINNT 0x0500


#include <windows.h>
#include <commctrl.h>  // InitCommonControls
#include <stdio.h>  // _fileno
#include <io.h>  // _get_osfhandle
#include <signal.h>  // signal


/* PyInstaller headers. */
#include "stb.h"
#include "pyi_global.h"  // PATH_MAX
#include "pyi_archive.h"
#include "pyi_path.h"
#include "pyi_utils.h"


static HANDLE hCtx = INVALID_HANDLE_VALUE;
static ULONG_PTR actToken;

#ifndef STATUS_SXS_EARLY_DEACTIVATION
#define STATUS_SXS_EARLY_DEACTIVATION 0xC015000F
#endif
 	
 	
int IsXPOrLater(void)
{
    OSVERSIONINFO osvi;
    
    ZeroMemory(&osvi, sizeof(OSVERSIONINFO));
    osvi.dwOSVersionInfoSize = sizeof(OSVERSIONINFO);

    GetVersionEx(&osvi);

    return ((osvi.dwMajorVersion > 5) ||
       ((osvi.dwMajorVersion == 5) && (osvi.dwMinorVersion >= 1)));
}

int CreateActContext(char *workpath, char *thisfile)
{
    char manifestpath[PATH_MAX];
    char basename[PATH_MAX];
    ACTCTX ctx;
    BOOL activated;
    HANDLE k32;
    HANDLE (WINAPI *CreateActCtx)(PACTCTX pActCtx);
    BOOL (WINAPI *ActivateActCtx)(HANDLE hActCtx, ULONG_PTR *lpCookie);

    // If not XP, nothing to do -- return OK
    if (!IsXPOrLater())
        return 1;
       
    /* Setup activation context */
    pyi_path_basename(basename, thisfile);
    pyi_path_join(manifestpath, workpath, basename);
    strcat(manifestpath, ".manifest");
    VS("LOADER: manifestpath: %s\n", manifestpath);
    
    k32 = LoadLibrary("kernel32");
    CreateActCtx = (void*)GetProcAddress(k32, "CreateActCtxA");
    ActivateActCtx = (void*)GetProcAddress(k32, "ActivateActCtx");
    
    if (!CreateActCtx || !ActivateActCtx)
    {
        VS("LOADER: Cannot find CreateActCtx/ActivateActCtx exports in kernel32.dll\n");
        return 0;
    }
    
    ZeroMemory(&ctx, sizeof(ctx));
    ctx.cbSize = sizeof(ACTCTX);
    ctx.lpSource = manifestpath;

    hCtx = CreateActCtx(&ctx);
    if (hCtx != INVALID_HANDLE_VALUE)
    {
        VS("LOADER: Activation context created\n");
        activated = ActivateActCtx(hCtx, &actToken);
        if (activated)
        {
            VS("LOADER: Activation context activated\n");
            return 1;
        }
    }

    hCtx = INVALID_HANDLE_VALUE;
    VS("LOADER: Error activating the context\n");
    return 0;
}

void ReleaseActContext(void)
{
    void (WINAPI *ReleaseActCtx)(HANDLE);
    BOOL (WINAPI *DeactivateActCtx)(DWORD dwFlags, ULONG_PTR ulCookie);
    HANDLE k32;

    if (!IsXPOrLater())
        return;

    k32 = LoadLibrary("kernel32");
    ReleaseActCtx = (void*)GetProcAddress(k32, "ReleaseActCtx");
    DeactivateActCtx = (void*)GetProcAddress(k32, "DeactivateActCtx");
    if (!ReleaseActCtx || !DeactivateActCtx)
    {
        VS("LOADER: Cannot find ReleaseActCtx/DeactivateActCtx exports in kernel32.dll\n");
        return;
    }
    __try
    {
        VS("LOADER: Deactivating activation context\n");
        if (!DeactivateActCtx(0, actToken))
            VS("LOADER: Error deactivating context!\n!");
        
        VS("LOADER: Releasing activation context\n");
        if (hCtx != INVALID_HANDLE_VALUE)
            ReleaseActCtx(hCtx);
        VS("LOADER: Done\n");
    }
    __except (STATUS_SXS_EARLY_DEACTIVATION)
    {
    	VS("LOADER: XS early deactivation; somebody left the activation context dirty, let's ignore the problem\n");
    }
}


// TODO This function is not called anywhere. Do we still need to init common controls? Or is it replaced by CreateActContext() function? Or is it safe to remove that?
static void init_launcher(void)
{
	InitCommonControls();
}


