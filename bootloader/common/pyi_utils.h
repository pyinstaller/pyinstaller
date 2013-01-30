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
 * Portable wrapper for some utility functions like getenv/setenv,
 * file path manipulation and other shared data types or functions.
 */


#ifndef HEADER_PYI_UTILS_H
#define HEADER_PYI_UTILS_H


/* Environment variables. */

char *pyi_getenv(const char *variable);
int pyi_setenv(const char *variable, const char *value);
int pyi_unsetenv(const char *variable);

/* Temporary files. */

int pyi_create_temp_path(ARCHIVE_STATUS *status);
void pyi_remove_temp_path(const char *dir);

/* Path manipulation. A new allocated buffer is returned. */
char *pyi_path_basename(const char *path);
char *pyi_path_dirname(const char *fullpath);
char *pyi_path_join(const char *path1, const char *path2);
char *pyi_path_normalize(const char *path);

/* File manipulation. */
FILE *pyi_open_target(const char *path, const char* name_);
int pyi_copy_file(const char *src, const char *dst, const char *filename);

/* Other routines. */
dylib_t pyi_dlopen(const char *dllpath);


#endif /* HEADER_PY_UTILS_H */
