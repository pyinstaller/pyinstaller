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


/* Path manipulation. Result is added to the supplied buffer. */
void *pyi_path_basename(char *result, char *path);
void *pyi_path_dirname(char *result, const char *path);
void *pyi_path_join(char *result, const char *path1, const char *path2);
void *pyi_path_normalize(char *result, const char *path);
// TODO implement.
//void *pyi_path_abspath(char *result, const char *path);


int pyi_path_executable(char *execfile, const char *appname);
void pyi_path_homepath(char *homepath, const char *executable);
void pyi_path_archivefile(char *archivefile, const char *executable);


#endif /* PYI_PATH_H */
