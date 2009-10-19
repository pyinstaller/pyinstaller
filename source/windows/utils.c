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
#include "utils.h"
#include <windows.h>
#include <commctrl.h> // InitCommonControls
#include <signal.h>
#include <memory.h>
#include <string.h>

void init_launcher(void)
{
	InitCommonControls();
}

int get_thisfile(char *thisfile, const char *programname)
{
	if (!GetModuleFileNameA(NULL, thisfile, _MAX_PATH)) {
		FATALERROR("System error - unable to load!");
		return -1;
	}
	
	return 0;
}

int get_thisfilew(LPWSTR thisfilew)
{
	if (!GetModuleFileNameW(NULL, thisfilew, _MAX_PATH)) {
		FATALERROR("System error - unable to load!");
		return -1;
	}
	
	return 0;
}

void get_homepath(char *homepath, const char *thisfile)
{
	char *p = NULL;
	
	strcpy(homepath, thisfile);
	for (p = homepath + strlen(homepath); *p != '\\' && p >= homepath + 2; --p);
	*++p = '\0';
}

void get_archivefile(char *archivefile, const char *thisfile)
{
	strcpy(archivefile, thisfile);
	strcpy(archivefile + strlen(archivefile) - 3, "pkg");
}

int set_enviroment(const ARCHIVE_STATUS *status)
{
	return 0;
}

int spawn(LPWSTR thisfile)
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

	VS("Setting up to run child\n");
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

	VS("Creating child process\n");
	if (CreateProcessW( 
			thisfile, // pointer to name of executable module 
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
		VS("Waiting for child process to finish...\n");
		WaitForSingleObject(pi.hProcess, INFINITE);
		GetExitCodeProcess(pi.hProcess, (unsigned long *)&rc);
	} else {
		FATALERROR("Error creating child process!\n");
		rc = -1;
	}
	return rc;
}