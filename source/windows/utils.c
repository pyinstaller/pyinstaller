/*
 * Bootloader for a packed executable.
 * Copyright (C) 2009, Lorenzo Masini
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
#define _WIN32_WINNT 0x0500
#include "pyi_unicode.h" 
#include "utils.h"
#include <windows.h>
#include <commctrl.h> // InitCommonControls
#include <signal.h>
#include <memory.h>
#include <string.h>


//unicode OK
TCHAR* basename (TCHAR *path)
{
  /* Search for the last directory separator in PATH.  */
  TCHAR *basename = _tcsrchr (path, _T('\\'));
  if (!basename) basename = _tcsrchr (path, _T('/'));
  
  /* If found, return the address of the following character,
     or the start of the parameter passed in.  */
  if (!basename)
  {
	  return path;
  }
  else
  {
	  return &basename[1]; // this will work OK, I guess.  At this stage, *basename points to either a slash or backslash, which can always
	                       // be stored as one 16-bit quantity (no surrogate pairs).
  }
}


static HANDLE hCtx = INVALID_HANDLE_VALUE;
static ULONG_PTR actToken;

#ifndef STATUS_SXS_EARLY_DEACTIVATION
#define STATUS_SXS_EARLY_DEACTIVATION 0xC015000F
#endif
 	
// unicode OK
int IsXPOrLater(void)
{
    OSVERSIONINFO osvi;
    
    ZeroMemory(&osvi, sizeof(OSVERSIONINFO));
    osvi.dwOSVersionInfoSize = sizeof(OSVERSIONINFO);

    GetVersionEx(&osvi);

    return ((osvi.dwMajorVersion > 5) ||
       ((osvi.dwMajorVersion == 5) && (osvi.dwMinorVersion >= 1)));
}

// unicode OK
int CreateActContext(TCHAR *workpath, TCHAR *thisfile)
{
    TCHAR manifestpath[_MAX_PATH + 1];
    ACTCTX ctx;
    BOOL activated;
    HANDLE k32;
    HANDLE (WINAPI *CreateActCtx)(PACTCTX pActCtx);
    BOOL (WINAPI *ActivateActCtx)(HANDLE hActCtx, ULONG_PTR *lpCookie);

    // If not XP, nothing to do -- return OK
    if (!IsXPOrLater())
        return 1;
       
    /* Setup activation context */
    _tcscpy(manifestpath, workpath);
    _tcscat(manifestpath, basename(thisfile));
    _tcscat(manifestpath, _T(".manifest"));
    VS(_T("manifestpath: %s\n"), manifestpath);
    
    k32 = LoadLibrary(_T("kernel32")); 
#ifdef UNICODE
    CreateActCtx = (void*)GetProcAddress(k32, "CreateActCtxW"); // unicode note: GetProcAddress is ascii only.
#else
	CreateActCtx = (void*)GetProcAddress(k32, "CreateActCtxA"); // unicode note: GetProcAddress is ascii only.
#endif
    ActivateActCtx = (void*)GetProcAddress(k32, "ActivateActCtx");
    
    if (!CreateActCtx || !ActivateActCtx)
    {
        VS(_T("Cannot find CreateActCtx/ActivateActCtx exports in kernel32.dll [%p %p]\n"),CreateActCtx,ActivateActCtx);
        return 0;
    }
    
    ZeroMemory(&ctx, sizeof(ctx));
    ctx.cbSize = sizeof(ACTCTX);
    ctx.lpSource = manifestpath;

    hCtx = CreateActCtx(&ctx);
    if (hCtx != INVALID_HANDLE_VALUE)
    {
        VS(_T("Activation context created\n"));
        activated = ActivateActCtx(hCtx, &actToken);
        if (activated)
        {
            VS(_T("Activation context activated\n"));
            return 1;
        }
    }

    hCtx = INVALID_HANDLE_VALUE;
    VS(_T("Error activating the context\n"));
    return 0;
}

// unicode OK
void ReleaseActContext(void)
{
    void (WINAPI *ReleaseActCtx)(HANDLE);
    BOOL (WINAPI *DeactivateActCtx)(DWORD dwFlags, ULONG_PTR ulCookie);
    HANDLE k32;

    if (!IsXPOrLater())
        return;

    k32 = LoadLibrary(_T("kernel32"));
    ReleaseActCtx = (void*)GetProcAddress(k32, "ReleaseActCtx");
    DeactivateActCtx = (void*)GetProcAddress(k32, "DeactivateActCtx");
    if (!ReleaseActCtx || !DeactivateActCtx)
    {
        VS(_T("Cannot find ReleaseActCtx/DeactivateActCtx exports in kernel32.dll [%p %p]\n"),ReleaseActCtx,DeactivateActCtx);
        return;
    }
    __try
    {
        VS(_T("Deactivating activation context\n"));
        if (!DeactivateActCtx(0, actToken))
            VS(_T("Error deactivating context!\n!"));
        
        VS(_T("Releasing activation context\n"));
        if (hCtx != INVALID_HANDLE_VALUE)
            ReleaseActCtx(hCtx);
        VS(_T("Done\n"));
    }
    __except (STATUS_SXS_EARLY_DEACTIVATION)
    {
    	VS(_T("XS early deactivation; somebody left the activation context dirty, let's ignore the problem\n"));
    }
}

// unicode OK
void init_launcher(void)
{
	InitCommonControls();
}

// unicode OK
int get_thisfile(TCHAR *thisfile, const TCHAR *programname)
{
	if (!GetModuleFileName(NULL, thisfile, _MAX_PATH)) {
		FATALERROR(_T("System error - unable to load!"));
		return -1;
	}
	
	return 0;
}

// unicode OK
int get_thisfilew(WCHAR *thisfilew)
{
	if (!GetModuleFileNameW(NULL, thisfilew, _MAX_PATH)) {
		FATALERROR(_T("System error - unable to load!"));
		return -1;
	}
	
	return 0;
}

// unicode OK
void get_homepath(TCHAR *homepath, const TCHAR *thisfile)
{
	TCHAR *p = NULL;
	TCHAR *pos = NULL;
	_tcscpy(homepath, thisfile);


	// in this below, this is a backward search for a backslash, making sure that the final path is at least two chars
	// long.  Presumably, under windows, this is the drive letter part, like "C:".  I'm not sure why this guard is needed,
	// as the path should always have a slash in it.  i.e., "c:\", especially since we are using 'thisfile' in order to
    // extract it.
	
#ifdef UNICODE
	pos = _tcsrchr(homepath,_T('\\'));

	
	if (pos)
	{
		_tcscpy(pos,_T("\\"));
	}
	else
	{
		_tprintf(_T("Error: could not generate the path of the file we are running.\n"));
		_tprintf(_T("  file: %s\n"),thisfile);
	}
#else
	for (p = homepath + _tcslen(homepath); *p != _T('\\') && p >= homepath + 2; --p); /// sorry, can't do this in unicode.
	*++p = '\0';
#endif

	return;
}

// unicode OK
void get_archivefile(TCHAR *archivefile, const TCHAR *thisfile)
{
	TCHAR*pos = NULL;
	_tcscpy(archivefile, thisfile);
	// remove the .exe and replace it with .pkg.
#ifdef UNICODE
	pos = _tcsrchr(archivefile,_T('.'));
	_tcscpy(pos, _T(".pkg"));  
#else
	strcpy(archivefile + _tcslen(archivefile) - 3, "pkg");  // sorry, can't do this in unicode.
#endif
	
	

	return;
	
}

//unicode OK
int set_enviroment(const ARCHIVE_STATUS *status)
{
	return 0;
}

int spawn(LPWSTR thisfilew) //unicode OK
{
	SECURITY_ATTRIBUTES sa;
	STARTUPINFOW si;
	PROCESS_INFORMATION pi;
	int rc = 0;

	// the parent process should ignore all signals it can
	signal(SIGABRT, SIG_IGN);
	signal(SIGINT, SIG_IGN);
	signal(SIGTERM, SIG_IGN);
	signal(SIGBREAK, SIG_IGN);

	VS(_T("Setting up to run child\n"));
	sa.nLength = sizeof(sa);
	sa.lpSecurityDescriptor = NULL;
	sa.bInheritHandle = TRUE;
	GetStartupInfoW(&si);
	si.lpReserved = NULL;
	si.lpDesktop = NULL;
	si.lpTitle = NULL;
	si.dwFlags = STARTF_USESTDHANDLES | STARTF_USESHOWWINDOW;
	si.wShowWindow = SW_NORMAL;
	si.hStdInput = (void*)_get_osfhandle(fileno(stdin));
	si.hStdOutput = (void*)_get_osfhandle(fileno(stdout));
	si.hStdError = (void*)_get_osfhandle(fileno(stderr));

	VS(_T("Creating child process\n"));
	if (CreateProcessW( 
			thisfilew, // pointer to name of executable module 
			GetCommandLineW(),  // pointer to command line string 
			&sa,  // pointer to process security attributes 
			NULL,  // pointer to thread security attributes 
			TRUE,  // handle inheritance flag 
			0,  // creation flags 
			NULL,  // pointer to new environment block 
			NULL,  // pointer to current directory name 
			&si,  // pointer to STARTUPINFO 
			&pi  // pointer to PROCESS_INFORMATION 
			)) {
		VS(_T("Waiting for child process to finish...\n"));
		WaitForSingleObject(pi.hProcess, INFINITE);
		GetExitCodeProcess(pi.hProcess, (unsigned long *)&rc);
	} else {
		FATALERROR(_T("Error creating child process!\n"));
		rc = -1;
	}
	return rc;
}
