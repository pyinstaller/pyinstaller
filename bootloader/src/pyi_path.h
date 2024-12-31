/*
 * ****************************************************************************
 * Copyright (c) 2013-2023, PyInstaller Development Team.
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

#include <stdio.h> /* FILE */

#include "pyi_global.h"


/* Path manipulation. Result is added to the supplied buffer. */
bool pyi_path_basename(char *result, const char *path);
bool pyi_path_dirname(char *result, const char *path);
char *pyi_path_join(char *result, const char *path1, const char *path2);
/* TODO implement. */
/* void *pyi_path_abspath(char *result, const char *path); */
int pyi_path_exists(char *path);

bool pyi_path_is_symlink(const char *path);

#ifdef _WIN32
FILE *pyi_path_fopen(const char *filename, const char *mode);
#else
#define pyi_path_fopen(x, y) fopen(x, y)
#endif

int pyi_path_mksymlink(const char *link_target, const char *link_name);

#endif /* PYI_PATH_H */
