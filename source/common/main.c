/*
 * Bootloader for a packed executable.
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
#include "pyi_unicode.h"
#include "utils.h"
#ifndef WIN32
#include <sys/wait.h>
#endif
#include "locale.h"


// To call TransformProcessType in the child process
#if defined(__APPLE__) && defined(WINDOWED)
#include "Processes.h"
#endif

#define MAX_STATUS_LIST 20

#if defined(WIN32) && defined(WINDOWED)
int APIENTRY WinMain( HINSTANCE hInstance, HINSTANCE hPrevInstance,
						LPSTR lpCmdLine, int nCmdShow )
#else
int main(int argc, char* argv[])
#endif
{
    /*  status_list[0] is reserved for the main process, the others for dependencies. */
    ARCHIVE_STATUS *status_list[MAX_STATUS_LIST];
    TCHAR thisfile[_MAX_PATH];
#ifdef WIN32
	WCHAR thisfilew[_MAX_PATH+1];
#endif
	char * loc;
    TCHAR homepath[_MAX_PATH];
    TCHAR archivefile[_MAX_PATH + 5];
    TCHAR MEIPASS2[_MAX_PATH + 11] = _T("_MEIPASS2=");
    int rc = 0;
    TCHAR *extractionpath = NULL;
#if defined(WIN32) && defined(WINDOWED)
    int argc = __argc;
	// UNICODE WARNING: we really should be looking at __targv here.  However, these
    // command line args end up being passed to the Python interpreter, which I believe
    // expects them in ascii.  Need to check on this.
    TCHAR **targv = __targv;
	char **argv = __argv;
#endif
    int i = 0;

    memset(&status_list, 0, MAX_STATUS_LIST * sizeof(ARCHIVE_STATUS *));
    if ((status_list[SELF] = (ARCHIVE_STATUS *) calloc(1, sizeof(ARCHIVE_STATUS))) == NULL){
        FATALERROR(_T("Cannot allocate memory for ARCHIVE_STATUS\n"));
        return -1;
    }

#ifdef UNICODE
	VS(_T("UNICODE SUPPORT = YES\n"));
	_tprintf(_T("Sizeof TCHAR: %d\n"),sizeof(TCHAR));
	//loc = setlocale(LC_ALL,""); // Problem: is calling this a mistake?  Leave things in the C locale?
#else
	VS(_T("UNICODE SUPPORT = NO\n"));
#endif

	get_thisfile(thisfile, argv[0]);
#ifdef WIN32
    get_thisfilew(thisfilew,NULL);
#endif

    get_archivefile(archivefile, thisfile);
    get_homepath(homepath, thisfile);

	VS(_T("THISFILE: %s\n"),thisfile);
	VS(_T("ARCHIVEFILE: %s\n"),archivefile);
	VS(_T("HOMEPATH: %s\n"),homepath);

    extractionpath = _tgetenv( _T("_MEIPASS2") );

	VS(_T("EXTRACTIONPATH: %s\n"),extractionpath);

    VS(_T("_MEIPASS2 is %s\n"), (extractionpath ? extractionpath : _T("NULL")));

    if (init(status_list[SELF], homepath, &thisfile[_tcslen(homepath)])) {
        if (init(status_list[SELF], homepath, &archivefile[_tcslen(homepath)])) {
            FATALERROR(_T("Cannot open self %s or archive %s\n"),thisfile, archivefile);
            return -1;
        }
    }

	VS(_T("DONE WITH INIT\n"));

    if (extractionpath) {
        VS(_T("Already in the child - running!\n"));
        /*  If binaries were extracted to temppath,
         *  we pass it through status variable
         */
        if (_tcscmp(homepath, extractionpath) != 0) {
            _tcscpy(status_list[SELF]->temppath, extractionpath);
#ifdef WIN32
            _tcscpy(status_list[SELF]->temppathraw, extractionpath);
#endif
        }
#if defined(__APPLE__) && defined(WINDOWED)
        ProcessSerialNumber psn = { 0, kCurrentProcess };
        OSStatus returnCode = TransformProcessType(&psn, kProcessTransformToForegroundApplication);
#endif
#ifdef WIN32
        CreateActContext(extractionpath, thisfile);
#endif
        rc = doIt(status_list[SELF], argc, argv);
#ifdef WIN32
        ReleaseActContext();
#endif
    } else {
        if (extractBinaries(status_list)) {
            VS(_T("Error extracting binaries\n"));
            return -1;
        }

        VS(_T("Executing self as child with "));
        /* run the "child" process, then clean up */
        _tcscat(MEIPASS2, status_list[SELF]->temppath[0] != 0 ? status_list[SELF]->temppath : homepath); // PROBLEM, what is going on here?
		VS(_T("MEIPASS2 = %s\n"),MEIPASS2);
        _tputenv(MEIPASS2);

        if (set_enviroment(status_list[SELF]) == -1)
            return -1;

#ifndef WIN32
        rc = spawn(thisfile, argv);
#else
        rc = spawn(thisfilew);
#endif

        VS(_T("Back to parent...\n"));
        if (status_list[SELF]->temppath[0] != 0)
            clear(status_list[SELF]->temppath);

        for (i = SELF; status_list[i] != NULL; i++) {
            VS(_T("Freeing status for %s\n"), status_list[i]->archivename);
            free(status_list[i]);
        }
    }

	VS(_T("Process %d ending normally (return code %d).\n"),getpid(),rc);
    return rc;
}
