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

/* File manipulation. */
FILE *pyi_open_target(const char *path, const char* name_);
int pyi_copy_file(const char *src, const char *dst, const char *filename);

/* Other routines. */
dylib_t pyi_utils_dlopen(const char *dllpath);
int pyi_utils_create_child(const char *thisfile, const int argc, char *const argv[]);
int pyi_utils_set_environment(const ARCHIVE_STATUS *status);


#endif /* HEADER_PY_UTILS_H */
