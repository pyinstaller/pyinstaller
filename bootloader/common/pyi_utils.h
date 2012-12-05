/*
 * Portable wrapper for some utility functions like getenv/setenv,
 * file path manipulation and other shared data types or functions.
 *
 * Copyright (C) 2012, Martin Zibricky
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
