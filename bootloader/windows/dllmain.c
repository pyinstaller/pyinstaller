/*
 * ****************************************************************************
 * Copyright (c) 2013, PyInstaller Development Team.
 * Distributed under the terms of the GNU General Public License with exception
 * for distributing bootloader.
 *
 * The full license is in the file COPYING.txt, distributed with this software.
 * ****************************************************************************
 */


/*
 * Bootloader for a DLL COM server.
 */


#include <windows.h>
#include <olectl.h>  // callSimpleEntryPoint
#include <memory.h>
#include <stdio.h>  // FILE
#include <string.h>


/* 
 * Use Sean's Tool Box -- public domain -- http://nothings.org/stb.h. 
 */
#define STB_DEFINE 1
#define STB_NO_REGISTRY 1  // Disable registry functions.
#define STB_NO_STB_STRINGS 1  // Disable config read/write functions.


/* PyInstaller headers. */
#include "stb.h"
#include "pyi_global.h"
#include "pyi_archive.h"
#include "pyi_python.h"
#include "pyi_pythonlib.h"
#include "pyi_launch.h"  // callSimpleEntryPoint
#include "utils.h"  // CreateActContext, ReleaseActContext


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
char here[PATH_MAX + 1];
int LoadPythonCom(ARCHIVE_STATUS *status);
void releasePythonCom(void);
HINSTANCE gInstance;
PyThreadState *thisthread = NULL;

int launch(ARCHIVE_STATUS *status, char const * archivePath, char  const * archiveName)
{
	PyObject *obHandle;
	int loadedNew = 0;
	char pathnm[PATH_MAX];

    VS("START");
	strcpy(pathnm, archivePath);
	strcat(pathnm, archiveName);
    /* Set up paths */
    if (pyi_arch_set_paths(status, archivePath, archiveName))
        return -1;
	VS("Got Paths");
    /* Open the archive */
    if (pyi_arch_open(status))
        return -1;
	VS("Opened Archive");
    /* Load Python DLL */
    if (pyi_pylib_attach(status, &loadedNew))
        return -1;

	if (loadedNew) {
		/* Start Python with silly command line */
		PI_PyEval_InitThreads();
		if (pyi_pylib_start_python(status, 1, (char**)&pathnm))
			return -1;
		VS("Started new Python");
		thisthread = PI_PyThreadState_Swap(NULL);
		PI_PyThreadState_Swap(thisthread);
	}
	else {
		VS("Attached to existing Python");

		/* start a mew interp */
		thisthread = PI_PyThreadState_Swap(NULL);
		PI_PyThreadState_Swap(thisthread);
		if (thisthread == NULL) {
			thisthread = PI_Py_NewInterpreter();
			VS("created thisthread");
		}
		else
			VS("grabbed thisthread");
		PI_PyRun_SimpleString("import sys;sys.argv=[]");
	}

	/* a signal to scripts */
	PI_PyRun_SimpleString("import sys;sys.frozen='dll'\n");
	VS("set sys.frozen");
	/* Create a 'frozendllhandle' as a counterpart to
	   sys.dllhandle (which is the Pythonxx.dll handle)
	*/
	obHandle = PI_Py_BuildValue("i", gInstance);
	PI_PySys_SetObject("frozendllhandle", obHandle);
	Py_XDECREF(obHandle);
    /* Import modules from archive - this is to bootstrap */
    if (pyi_pylib_import_modules(status))
        return -1;
	VS("Imported Modules");
    /* Install zlibs - now import hooks are in place */
    if (pyi_pylib_install_zlibs(status))
        return -1;
	VS("Installed Zlibs");
    /* Run scripts */
    if (pyi_pylib_run_scripts(status))
        return -1;
	VS("All scripts run");
    if (PI_PyErr_Occurred()) {
		// PI_PyErr_Print();
		//PI_PyErr_Clear();
		VS("Some error occurred");
    }
	VS("PGL released");
	// Abandon our thread state.
	PI_PyEval_ReleaseThread(thisthread);
    VS("OK.");
    return 0;
}
void startUp()
{
	ARCHIVE_STATUS *archive_status;
	char thisfile[PATH_MAX];
	char *p;
	int len;
	memset(archive_status, 0, sizeof(ARCHIVE_STATUS *));
	
	if (!GetModuleFileNameA(gInstance, thisfile, PATH_MAX)) {
		FATALERROR("System error - unable to load!");
		return;
	}
	// fill in here (directory of thisfile)
	//GetModuleFileName returns an absolute path
	strcpy(here, thisfile);
	for (p=here+strlen(here); *p != '\\' && p >= here+2; --p);
	*++p = '\0';
	len = p - here;
	//VS(here);
	//VS(&thisfile[len]);
	launch(archive_status, here, &thisfile[len]);
	LoadPythonCom(archive_status);
	// Now Python is up and running (any scripts have run)
}

BOOL WINAPI DllMain(HINSTANCE hInstance, DWORD dwReason, LPVOID lpReserved)
{
	if ( dwReason == DLL_PROCESS_ATTACH) {
		VS("Attach from thread %x", GetCurrentThreadId());
		gInstance = hInstance;
	}
	else if ( dwReason == DLL_PROCESS_DETACH ) {
		VS("Process Detach");
		//if (gPythoncom)
		//	releasePythonCom();
		//pyi_pylib_finalize();
	}

	return TRUE; 
}

int LoadPythonCom(ARCHIVE_STATUS *status)
{
	char dllpath[PATH_MAX+1];
	VS("Loading Pythoncom");
	// see if pythoncom is already loaded
	sprintf(dllpath, "pythoncom%02d.dll", pyi_arch_get_pyversion(status));
	gPythoncom = GetModuleHandleA(dllpath);
	if (gPythoncom == NULL) {
		sprintf(dllpath, "%spythoncom%02d.dll", here, pyi_arch_get_pyversion(status));
		//VS(dllpath);
		gPythoncom = LoadLibraryExA( dllpath, // points to name of executable module 
					   NULL, // HANDLE hFile, // reserved, must be NULL 
					   LOAD_WITH_ALTERED_SEARCH_PATH // DWORD dwFlags // entry-point execution flag 
					  ); 
	}
	if (!gPythoncom) {
		VS("Pythoncom failed to load");
		return -1;
	}
	// debugging
	GetModuleFileNameA(gPythoncom, dllpath, PATH_MAX);
	VS(dllpath);

	Pyc_DllCanUnloadNow = (__PROC__DllCanUnloadNow)GetProcAddress(gPythoncom, "DllCanUnloadNow");
	Pyc_DllGetClassObject = (__PROC__DllGetClassObject)GetProcAddress(gPythoncom, "DllGetClassObject");
	// DllRegisterServerEx etc are mainly used for "scripts", so that regsvr32.exe can be run on
	// a .py file, for example.  They aren't really relevant here.
	Pyc_DllRegisterServerEx = (__PROC__DllRegisterServerEx)GetProcAddress(gPythoncom, "DllRegisterServerEx");
	Pyc_DllUnregisterServerEx = (__PROC__DllUnregisterServerEx)GetProcAddress(gPythoncom, "DllUnregisterServerEx");
	PyCom_CoUninitialize = (__PROC__PyCom_CoUninitialize)GetProcAddress(gPythoncom, "PyCom_CoUninitialize");
	if (Pyc_DllGetClassObject == NULL) {
		VS("Couldn't get DllGetClassObject from pythoncom!");
		return -1;
	}
	if (PyCom_CoUninitialize == NULL) {
		VS("Couldn't get PyCom_CoUninitialize from pythoncom!");
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

	VS("DllCanUnloadNow from thread %x", GetCurrentThreadId());
	if (gPythoncom == 0)
		startUp();
	rc = Pyc_DllCanUnloadNow();
	VS("DllCanUnloadNow returns %x", rc);
	//if (rc == S_OK)
	//	PyCom_CoUninitialize();
	return rc;
}

//__declspec(dllexport) int __stdcall DllGetClassObject(void *rclsid, void *riid, void *ppv)
HRESULT __stdcall DllGetClassObject(REFCLSID rclsid, REFIID riid, LPVOID *ppv)
{
	HRESULT rc;

	VS("DllGetClassObject from thread %x", GetCurrentThreadId());
	if (gPythoncom == 0)
		startUp();
	rc = Pyc_DllGetClassObject(rclsid, riid, ppv);
	VS("DllGetClassObject set %x and returned %x", *ppv, rc);

	return rc;
}

__declspec(dllexport) int DllRegisterServerEx(LPCSTR fileName)
{
	VS("DllRegisterServerEx from thread %x", GetCurrentThreadId());
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
