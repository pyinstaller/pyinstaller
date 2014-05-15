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


/*
 * Functions in this file are windows specific and are mostly related to handle
 * Side-by-Side assembly:
 *
 * https://en.wikipedia.org/wiki/Side-by-side_assembly
 */

#ifdef _WIN32

/* windows.h will use API for WinServer 2003 with SP1 and WinXP with SP2 */
#define _WIN32_WINNT 0x0502


#include <windows.h>
#include <commctrl.h>  // InitCommonControls
#include <stdio.h>  // _fileno
#include <io.h>  // _get_osfhandle
#include <signal.h>  // signal


/* PyInstaller headers. */
#include "msvc_stdint.h"  // int32_t
#include "pyi_global.h"  // PATH_MAX
#include "pyi_archive.h"
#include "pyi_path.h"
#include "pyi_utils.h"


static HANDLE hCtx = INVALID_HANDLE_VALUE;
static ULONG_PTR actToken;

#ifndef STATUS_SXS_EARLY_DEACTIVATION
#define STATUS_SXS_EARLY_DEACTIVATION 0xC015000F
#endif
 	
 	
int CreateActContext(const char *workpath, const char *thisfile)
{
    char manifestpath[PATH_MAX];
    char basename[PATH_MAX];
    ACTCTX ctx;
    BOOL activated;
    HANDLE k32;
    HANDLE (WINAPI *CreateActCtx)(PACTCTX pActCtx);
    BOOL (WINAPI *ActivateActCtx)(HANDLE hActCtx, ULONG_PTR *lpCookie);

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

    k32 = LoadLibrary("kernel32");
    ReleaseActCtx = (void*)GetProcAddress(k32, "ReleaseActCtx");
    DeactivateActCtx = (void*)GetProcAddress(k32, "DeactivateActCtx");
    if (!ReleaseActCtx || !DeactivateActCtx)
    {
        VS("LOADER: Cannot find ReleaseActCtx/DeactivateActCtx exports in kernel32.dll\n");
        return;
    }

    // TODO mingw (gcc) does not support '__try', '__except' - probably just drop it if there is no other workaround.
    /*__try
    {*/

        VS("LOADER: Deactivating activation context\n");
        if (!DeactivateActCtx(0, actToken))
            VS("LOADER: Error deactivating context!\n!");
        
        VS("LOADER: Releasing activation context\n");
        if (hCtx != INVALID_HANDLE_VALUE)
            ReleaseActCtx(hCtx);
        VS("LOADER: Done\n");

    // TODO mingw (gcc) does not support '__try', '__except' - probably just drop it if there is no other workaround.
    /*}
    __except (STATUS_SXS_EARLY_DEACTIVATION)
    {
    	VS("LOADER: XS early deactivation; somebody left the activation context dirty, let's ignore the problem\n");
    }*/
}


// TODO This function is not called anywhere. Do we still need to init common controls? Or is it replaced by CreateActContext() function? Or is it safe to remove that?
static void init_launcher(void)
{
	InitCommonControls();
}


/*
 * Convert wchar_t (UTF16) into char (UTF8).
 */
char * pyi_win32_utils_to_utf8(char *buffer, const wchar_t *str, int n)
{
   int i=0;
   int32_t c;
   --n;
   while (*str) {
      if (*str < 0x80) {
         if (i+1 > n) return NULL;
         buffer[i++] = (char) *str++;
      } else if (*str < 0x800) {
         if (i+2 > n) return NULL;
         buffer[i++] = 0xc0 + (*str >> 6);
         buffer[i++] = 0x80 + (*str & 0x3f);
         str += 1;
      } else if (*str >= 0xd800 && *str < 0xdc00) {
         if (i+4 > n) return NULL;
         c = ((str[0] - 0xd800) << 10) + ((str[1]) - 0xdc00) + 0x10000;
         buffer[i++] = 0xf0 + (c >> 18);
         buffer[i++] = 0x80 + ((c >> 12) & 0x3f);
         buffer[i++] = 0x80 + ((c >>  6) & 0x3f);
         buffer[i++] = 0x80 + ((c      ) & 0x3f);
         str += 2;
      } else if (*str >= 0xdc00 && *str < 0xe000) {
         return NULL;
      } else {
         if (i+3 > n) return NULL;
         buffer[i++] = 0xe0 + (*str >> 12);
         buffer[i++] = 0x80 + ((*str >> 6) & 0x3f);
         buffer[i++] = 0x80 + ((*str     ) & 0x3f);
         str += 1;
      }
   }
   buffer[i] = 0;
   return buffer;
}


/*
 * Convert char (UTF8) into wchar_t (UTF16).
 */
wchar_t * pyi_win32_utils_from_utf8(wchar_t *buffer, char *ostr, int n)
{
   unsigned char *str = (unsigned char *) ostr;
   uint32_t c;
   int i=0;
   --n;
   while (*str) {
      if (i >= n)
         return NULL;
      if (!(*str & 0x80))
         buffer[i++] = *str++;
      else if ((*str & 0xe0) == 0xc0) {
         if (*str < 0xc2) return NULL;
         c = (*str++ & 0x1f) << 6;
         if ((*str & 0xc0) != 0x80) return NULL;
         buffer[i++] = c + (*str++ & 0x3f);
      } else if ((*str & 0xf0) == 0xe0) {
         if (*str == 0xe0 && (str[1] < 0xa0 || str[1] > 0xbf)) return NULL;
         if (*str == 0xed && str[1] > 0x9f) return NULL; // str[1] < 0x80 is checked below
         c = (*str++ & 0x0f) << 12;
         if ((*str & 0xc0) != 0x80) return NULL;
         c += (*str++ & 0x3f) << 6;
         if ((*str & 0xc0) != 0x80) return NULL;
         buffer[i++] = c + (*str++ & 0x3f);
      } else if ((*str & 0xf8) == 0xf0) {
         if (*str > 0xf4) return NULL;
         if (*str == 0xf0 && (str[1] < 0x90 || str[1] > 0xbf)) return NULL;
         if (*str == 0xf4 && str[1] > 0x8f) return NULL; // str[1] < 0x80 is checked below
         c = (*str++ & 0x07) << 18;
         if ((*str & 0xc0) != 0x80) return NULL;
         c += (*str++ & 0x3f) << 12;
         if ((*str & 0xc0) != 0x80) return NULL;
         c += (*str++ & 0x3f) << 6;
         if ((*str & 0xc0) != 0x80) return NULL;
         c += (*str++ & 0x3f);
         // utf-8 encodings of values used in surrogate pairs are invalid
         if ((c & 0xFFFFF800) == 0xD800) return NULL;
         if (c >= 0x10000) {
            c -= 0x10000;
            if (i + 2 > n) return NULL;
            buffer[i++] = 0xD800 | (0x3ff & (c >> 10));
            buffer[i++] = 0xDC00 | (0x3ff & (c      ));
         }
      } else
         return NULL;
   }
   buffer[i] = 0;
   return buffer;
}

#endif // _WIN32
