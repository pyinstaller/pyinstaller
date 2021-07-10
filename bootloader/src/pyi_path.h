/*
 * ****************************************************************************
 * Copyright (c) 2013-2021, PyInstaller Development Team.
 *
 * Distributed under the terms of the GNU General Public License (version 2
 * or later) with exception for distributing the bootloader.
 *
 * The full license is in the file COPYING.txt, distributed with this software.
 *
 * SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
 * ****************************************************************************
 */

/*
 * Path manipulation utilities.
 */

#ifndef PYI_PATH_H
#define PYI_PATH_H

#include "pyi_global.h"

/* Path manipulation. Result is added to the supplied buffer. */
bool pyi_path_basename(char *result, const char *path);
bool pyi_path_dirname(char *result, const char *path);
char *pyi_path_join(char *result, const char *path1, const char *path2);
int pyi_path_fullpath(char *abs, size_t abs_size, const char *rel);
/* TODO implement. */
/* void *pyi_path_abspath(char *result, const char *path); */
int pyi_path_exists(char *path);

bool pyi_path_executable(char *execfile, const char *appname);
bool pyi_path_homepath(char *homepath, const char *executable);
bool pyi_path_archivefile(char *archivefile, const char *executable);

#ifdef _WIN32
FILE *pyi_path_fopen(const char *filename, const char *mode);
#else
    #define pyi_path_fopen(x, y)    fopen(x, y)
#endif
#define pyi_path_fclose(x)    fclose(x)

#endif  /* PYI_PATH_H */
