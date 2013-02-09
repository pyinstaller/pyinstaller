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
 * Path manipulation utilities.
 */


#ifndef PYI_PATH_H
#define PYI_PATH_H


int pyi_path_executable(char *execfile, const char *appname);
void pyi_path_homepath(char *homepath, const char *executable);
void pyi_path_archivefile(char *archivefile, const char *executable);


#endif /* PYI_PATH_H */
