#include "launch.h"
#include <windows.h>
#include <signal.h>

int relaunch(char *thisfile, char *workpath)
{
	char envvar[_MAX_PATH + 12];
	SECURITY_ATTRIBUTES sa;
	STARTUPINFO si;
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
	GetStartupInfo(&si);
	si.lpReserved = NULL;
	si.lpDesktop = NULL;
	si.lpTitle = NULL;
	si.dwFlags = STARTF_USESTDHANDLES | STARTF_USESHOWWINDOW;
	si.wShowWindow = SW_NORMAL;
	si.hStdInput = (void*)_get_osfhandle(fileno(stdin));
	si.hStdOutput = (void*)_get_osfhandle(fileno(stdout));
	si.hStdError = (void*)_get_osfhandle(fileno(stderr));
	/* tell pass 2 where we extracted to */
	VS("Setting magic environment var\n");
	strcpy(envvar, "_MEIPASS2=");
	strcat(envvar, workpath);
	_putenv(envvar);
	VS("Creating child process\n");
	if (CreateProcess( 
			thisfile, // pointer to name of executable module 
			GetCommandLine(),  // pointer to command line string 
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
	}
	else {
		FATALERROR("Error creating child process!\n");
		rc = -1;
	}
	return rc;
}


#ifdef _CONSOLE
int main(int argc, char* argv[])
#else
int APIENTRY WinMain( HINSTANCE hInstance, HINSTANCE hPrevInstance,
						LPSTR lpCmdLine, int nCmdShow )
#endif
{
	char here[_MAX_PATH + 1];
	char thisfile[_MAX_PATH + 1];
	int rc = 0;
	char *workpath = NULL;
	char *p;
	int len;
#ifndef _CONSOLE
	int argc = __argc;
	char **argv = __argv;
#endif

	// fill in thisfile
	if (!GetModuleFileNameA(NULL, thisfile, _MAX_PATH)) {
		FATALERROR("System error - unable to load!");
		return -1;
	}
	p = thisfile+strlen(thisfile) - 4;
	if (strnicmp(p, ".exe", 4) != 0)
		strcat(thisfile, ".exe");

	// fill in here (directory of thisfile)
	//GetModuleFileName returns an absolute path
	strcpy(here, thisfile);
	for (p=here+strlen(here); *p != '\\' && p >= here+2; --p);
	*++p = '\0';
	len = p - here;

	workpath = getenv( "_MEIPASS2" );
    rc = init(here, &thisfile[len], workpath);
    if (rc)
        return rc;
	if (workpath) {
		// we're the "child" process
		rc = doIt(argc, argv);
		finalizePython();
	}
	else {
		if (extractBinaries(&workpath)) {
			VS("Error extracting binaries");
			return -1;
		}
        // if workpath got set to non-NULL, we've extracted stuff
		if (workpath) {
			// run the "child" process, then clean up
			rc = relaunch(thisfile, workpath);
		}
		else {
			// no "child" process necessary
			rc = doIt(argc, argv);
			finalizePython();
		}
        cleanUp();
	}
	return rc;
}
