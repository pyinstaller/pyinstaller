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

#ifndef HEADER_PYI_UTILS_H
#define HEADER_PYI_UTILS_H

#include "pyi_archive.h"

#ifndef _WIN32
#include <sys/types.h> /* pid_t */
#endif

// some platforms do not provide strnlen
#ifndef HAVE_STRNLEN
size_t strnlen(const char *str, size_t n);
#endif

/* Environment variables. */
char *pyi_getenv(const char *variable);
int pyi_setenv(const char *variable, const char *value);
int pyi_unsetenv(const char *variable);

/* Temporary directory. */
int pyi_create_tempdir(char *buff, const char *runtime_tmpdir);

/* Recursive directory deletion. */
void pyi_recursive_rmdir(const char *dir);

/* File manipulation. */
int pyi_create_parent_directory(const char *path, const char *name_);
FILE *pyi_open_target_file(const char *path, const char* name_);
int pyi_copy_file(const char *src, const char *dst, const char *filename);

/* Other routines. */
dylib_t pyi_utils_dlopen(const char *dllpath);
int pyi_utils_dlclose(dylib_t dll);
int pyi_utils_create_child(const char *thisfile, const ARCHIVE_STATUS *status,
                           const int argc, char *const argv[]);
#ifndef _WIN32
pid_t pyi_utils_get_child_pid();
void pyi_utils_reraise_child_signal();
#endif

#if !defined(_WIN32) && !defined(__APPLE__)
int pyi_utils_set_library_search_path(const char *path);
int pyi_utils_replace_process(const char *thisfile, const int argc, char *const argv[]);
#endif

/* Argument handling */
int pyi_utils_initialize_args(const int argc, char *const argv[]);
int pyi_utils_append_to_args(const char *arg);
void pyi_utils_get_args(int *argc, char ***argv);
void pyi_utils_free_args();

/* Magic pattern matching */
extern const unsigned char MAGIC_BASE[8];
uint64_t pyi_utils_find_magic_pattern(FILE *fp, const unsigned char *magic, size_t magic_len);

#endif  /* HEADER_PY_UTILS_H */
