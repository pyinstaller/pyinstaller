/*
 * Bootloader for a DLL COM server.
 * Copyright (C) 2005, Giovanni Bajo
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
#include "launch.h"
#include "utils.h"
#include <windows.h>
#include <olectl.h>
#include <memory.h>
#include <string.h>

typedef int (__stdcall *__PROC__DllCanUnloadNow) (void);
__PROC__DllCanUnloadNow Pyc_DllCanUnloadNow = NULL;
typedef HRESULT (__stdcall *__PROC__DllGetClassObject) (REFCLSID, REFIID, LPVOID *);
__PROC__DllGetClassObject Pyc_DllGetClassObject = NULL;
typedef int (__cdecl *__PROC__DllRegisterServerEx) (const char *);
__PROC__DllRegisterServerEx Pyc_DllRegisterServerEx = NULL;
typedef int (__cdecl *__PROC__DllUnregisterServerEx) (const char *);
__PROC__DllUnregisterServerEx Pyc_DllUnregisterServerEx = NULL;
typedef void (__cdecl *__PROC__PyCom_CoUninitialize) (void);
__PROC__PyCom_CoUninitialize PyCom_CoUninitialize = NULL;

HINSTANCE gPythoncom = 0;
TCHAR here[_MAX_PATH + 1];
int LoadPythonCom(ARCHIVE_STATUS *status);
void releasePythonCom(void);
HINSTANCE gInstance;
PyThreadState *thisthread = NULL;

int launch(ARCHIVE_STATUS *status, TCHAR const * archivePath, TCHAR  const * archiveName)
{
	PyObject *obHandle;
	int loadedNew = 0;
	TCHAR pathnm[_MAX_PATH];

    VS(_T("START"));
	_tcscpy(pathnm, archivePath);
	_tcscpy(pathnm, archiveName);
    /* Set up paths */
    if (setPaths(status, archivePath, archiveName))
        return -1;
	VS(_T("Got Paths"));
    /* Open the archive */
    if (openArchive(status))
        return -1;
	VS(_T("Opened Archive"));
    /* Load Python DLL */
    if (attachPython(status, &loadedNew))
        return -1;

	if (loadedNew) {
		/* Start Python with silly command line */
		PI_PyEval_InitThreads();
		if (startPython(status, 0, NULL))   // argv is never used in startPython. So, no arguments.
			return -1;
		VS(_T("Started new Python"));
		thisthread = PI_PyThreadState_Swap(NULL);
		PI_PyThreadState_Swap(thisthread);
	}
	else {
		VS(_T("Attached to existing Python"));

		/* start a mew interp */
		thisthread = PI_PyThreadState_Swap(NULL);
		PI_PyThreadState_Swap(thisthread);
		if (thisthread == NULL) {
			thisthread = PI_Py_NewInterpreter();
			VS(_T("created thisthread"));
		}
		else
			VS(_T("grabbed thisthread"));
		PI_PyRun_SimpleString("import sys;sys.argv=[]");
	}

	/* a signal to scripts */
	PI_PyRun_SimpleString("import sys;sys.frozen='dll'\n");
	VS(_T("set sys.frozen"));
	/* Create a 'frozendllhandle' as a counterpart to
	   sys.dllhandle (which is the Pythonxx.dll handle)
	*/
	obHandle = PI_Py_BuildValue("i", gInstance);
	PI_PySys_SetObject("frozendllhandle", obHandle);
	Py_XDECREF(obHandle);
    /* Import modules from archive - this is to bootstrap */
    if (importModules(status))
        return -1;
	VS(_T("Imported Modules"));
    /* Install zlibs - now import hooks are in place */
    if (installZlibs(status))
        return -1;
	VS(_T("Installed Zlibs"));
    /* Run scripts */
    if (runScripts(status))
        return -1;
	VS(_T("All scripts run"));
    if (PI_PyErr_Occurred()) {
		// PI_PyErr_Print();
		//PI_PyErr_Clear();
		VS(_T("Some error occurred"));
    }
	VS(_T("PGL released"));
	// Abandon our thread state.
	PI_PyEval_ReleaseThread(thisthread);
    VS(_T("OK."));
    return 0;
}
void startUp()
{
	ARCHIVE_STATUS *status_list[20];
	TCHAR thisfile[_MAX_PATH + 1];
	//char *p;
	int len;
	memset(status_list, 0, 20 * sizeof(ARCHIVE_STATUS *));
	
	if (!GetModuleFileName(gInstance, thisfile, _MAX_PATH)) {
		FATALERROR(_T("System error - unable to load!"));
		return;
	}
	// fill in here (directory of thisfile)
	//GetModuleFileName returns an absolute path
	_tcscpy(here, thisfile);

	// COMPLETELY UNTESTED!  The following two lines replace the two commented out ones.
	get_homepath(here,thisfile); // not a good name for what this function does.
	len = _tcslen(here);
	//for (p=here+_tcslen(here); *p != '\\' && p >= here+2; --p);
	//*++p = '\0';
	
	//VS(here);
	//VS(&thisfile[len]);
	launch(status_list[SELF], here, &thisfile[len]);
	LoadPythonCom(status_list[SELF]);
	// Now Python is up and running (any scripts have run)
}

BOOL WINAPI DllMain(HINSTANCE hInstance, DWORD dwReason, LPVOID lpReserved)
{
	if ( dwReason == DLL_PROCESS_ATTACH) {
		VS(_T("Attach from thread %x"), GetCurrentThreadId());
		gInstance = hInstance;
	}
	else if ( dwReason == DLL_PROCESS_DETACH ) {
		VS(_T("Process Detach"));
		//if (gPythoncom)
		//	releasePythonCom();
		//finalizePython();
	}

	return TRUE; 
}

int LoadPythonCom(ARCHIVE_STATUS *status)
{
	TCHAR dllpath[_MAX_PATH+1];
	VS(_T("Loading Pythoncom"));
	// see if pythoncom is already loaded
	_stprintf(dllpath, _T("pythoncom%02d.dll"), getPyVersion(status));
	gPythoncom = GetModuleHandle(dllpath);
	if (gPythoncom == NULL) {
		_stprintf(dllpath, _T("%spythoncom%02d.dll"), here, getPyVersion(status));
		//VS(dllpath);
		gPythoncom = LoadLibraryEx( dllpath, // points to name of executable module 
					   NULL, // HANDLE hFile, // reserved, must be NULL 
					   LOAD_WITH_ALTERED_SEARCH_PATH // DWORD dwFlags // entry-point execution flag 
					  ); 
	}
	if (!gPythoncom) {
		VS(_T("Pythoncom failed to load"));
		return -1;
	}
	// debugging
	GetModuleFileName(gPythoncom, dllpath, _MAX_PATH);
	VS(dllpath);

	Pyc_DllCanUnloadNow = (__PROC__DllCanUnloadNow)GetProcAddress(gPythoncom, "DllCanUnloadNow");
	Pyc_DllGetClassObject = (__PROC__DllGetClassObject)GetProcAddress(gPythoncom, "DllGetClassObject");
	// DllRegisterServerEx etc are mainly used for "scripts", so that regsvr32.exe can be run on
	// a .py file, for example.  They aren't really relevant here.
	Pyc_DllRegisterServerEx = (__PROC__DllRegisterServerEx)GetProcAddress(gPythoncom, "DllRegisterServerEx");
	Pyc_DllUnregisterServerEx = (__PROC__DllUnregisterServerEx)GetProcAddress(gPythoncom, "DllUnregisterServerEx");
	PyCom_CoUninitialize = (__PROC__PyCom_CoUninitialize)GetProcAddress(gPythoncom, "PyCom_CoUninitialize");
	if (Pyc_DllGetClassObject == NULL) {
		VS(_T("Couldn't get DllGetClassObject from pythoncom!"));
		return -1;
	}
	if (PyCom_CoUninitialize == NULL) {
		VS(_T("Couldn't get PyCom_CoUninitialize from pythoncom!"));
		return -1;
	}
	return 0;
}
void releasePythonCom(void)
{
	if (gPythoncom) {
		PyCom_CoUninitialize();
		FreeLibrary(gPythoncom);
		gPythoncom = 0;
	}
}
//__declspec(dllexport) int __stdcall DllCanUnloadNow(void)
//__declspec(dllexport)
//STDAPI
HRESULT __stdcall DllCanUnloadNow(void)
{
	HRESULT rc;

	VS(_T("DllCanUnloadNow from thread %x"), GetCurrentThreadId());
	if (gPythoncom == 0)
		startUp();
	rc = Pyc_DllCanUnloadNow();
	VS(_T("DllCanUnloadNow returns %x"), rc);
	//if (rc == S_OK)
	//	PyCom_CoUninitialize();
	return rc;
}

//__declspec(dllexport) int __stdcall DllGetClassObject(void *rclsid, void *riid, void *ppv)
HRESULT __stdcall DllGetClassObject(REFCLSID rclsid, REFIID riid, LPVOID *ppv)
{
	HRESULT rc;

	VS(_T("DllGetClassObject from thread %x"), GetCurrentThreadId());
	if (gPythoncom == 0)
		startUp();
	rc = Pyc_DllGetClassObject(rclsid, riid, ppv);
	VS(_T("DllGetClassObject set %x and returned %x"), *ppv, rc);

	return rc;
}

__declspec(dllexport) int DllRegisterServerEx(LPCSTR fileName)
{
	VS(_T("DllRegisterServerEx from thread %x"), GetCurrentThreadId());
	if (gPythoncom == 0)
		startUp();
	return Pyc_DllRegisterServerEx(fileName);
}

__declspec(dllexport) int DllUnregisterServerEx(LPCSTR fileName)
{
	if (gPythoncom == 0)
		startUp();
	return Pyc_DllUnregisterServerEx(fileName);
}

STDAPI DllRegisterServer()
{
	int rc, pyrc;
	if (gPythoncom == 0)
		startUp();
	PI_PyEval_AcquireThread(thisthread);
	rc = callSimpleEntryPoint("DllRegisterServer", &pyrc);
	PI_PyEval_ReleaseThread(thisthread);
	return rc==0 ? pyrc : SELFREG_E_CLASS;
}

STDAPI DllUnregisterServer()
{
	int rc, pyrc;
	if (gPythoncom == 0)
		startUp();
	PI_PyEval_AcquireThread(thisthread);
	rc = callSimpleEntryPoint("DllUnregisterServer", &pyrc);
	PI_PyEval_ReleaseThread(thisthread);
	return rc==0 ? pyrc : SELFREG_E_CLASS;
}
