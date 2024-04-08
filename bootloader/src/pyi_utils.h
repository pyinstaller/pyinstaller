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
 * Portable wrapper for some utility functions like getenv/setenv,
 * file path manipulation and other shared data types or functions.
 */

#ifndef PYI_UTILS_H
#define PYI_UTILS_H

#include <stdio.h> /* FILE */
#include <inttypes.h> /* uint64_t */

typedef struct _pyi_context PYI_CONTEXT;

/* Environment variables. */
char *pyi_getenv(const char *variable);
int pyi_setenv(const char *variable, const char *value);
int pyi_unsetenv(const char *variable);

/* Temporary top-level application directory (onefile). */
int pyi_create_temporary_application_directory(PYI_CONTEXT *pyi_ctx);

/* Recursive directory deletion. */
int pyi_recursive_rmdir(const char *dir);

/* Misc. file/directory manipulation. */
int pyi_create_parent_directory_tree(const PYI_CONTEXT *pyi_ctx, const char *prefix_path, const char *filename);
int pyi_copy_file(const char *src_filename, const char *dest_filename);

/* Shared library loading. */
dylib_t pyi_utils_dlopen(const char *filename);
int pyi_utils_dlclose(dylib_t handle);

/* Child process */
int pyi_utils_create_child(PYI_CONTEXT *pyi_ctx);

#if !defined(_WIN32) && !defined(__APPLE__)
int pyi_utils_set_library_search_path(const char *path);
#endif

/* Argument handling (POSIX only) */
#if !defined(_WIN32)
int pyi_utils_initialize_args(PYI_CONTEXT *pyi_ctx, const int argc, char *const argv[]);
int pyi_utils_append_to_args(PYI_CONTEXT *pyi_ctx, const char *arg);
void pyi_utils_free_args(PYI_CONTEXT *pyi_ctx);
#endif

/* Magic pattern matching */
extern const unsigned char MAGIC_BASE[8];
uint64_t pyi_utils_find_magic_pattern(FILE *fp, const unsigned char *magic, size_t magic_len);

#endif /* PYI_UTILS_H */
