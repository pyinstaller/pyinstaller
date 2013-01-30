/*
 * ****************************************************************************
 * Copyright (c) 2013, PyInstaller Development Team.
 * Distributed under the terms of the GNU General Public License with exception
 * for distributing bootloader.
 *
 * The full license is in the file COPYING.txt, distributed with this software.
 * ****************************************************************************
 */


void init_launcher(void);
int get_thisfile(char *thisfile, const char *programname);
#ifdef WIN32
int CreateActContext(char *workpath, char *thisfile);
void ReleaseActContext(void);
int get_thisfilew(LPWSTR thisfilew);
#endif
void get_homepath(char *homepath, const char *thisfile);
void get_archivefile(char *archivefile, const char *thisfile);
int set_environment(const ARCHIVE_STATUS *status);
#ifndef WIN32
int spawn(const char *thisfile, char *const argv[]);
#else
int spawn(LPWSTR thisfile);
#endif
