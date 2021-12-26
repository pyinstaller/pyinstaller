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
 * Portable wrapper for some utility functions like getenv/setenv,
 * file path manipulation and other shared data types or functions.
 */

#ifndef HEADER_PYI_UTILS_H
#define HEADER_PYI_UTILS_H

#include "pyi_archive.h"

// some platforms do not provide strnlen
#ifndef HAVE_STRNLEN
size_t strnlen(const char *str, size_t n);
#endif

// some platforms do not provide strndup
#ifndef HAVE_STRNDUP
char *strndup(const char * str, size_t n);
#endif

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
int pyi_utils_dlclose(dylib_t dll);
int pyi_utils_create_child(const char *thisfile, const ARCHIVE_STATUS *status,
                           const int argc, char *const argv[]);
int pyi_utils_set_environment(const ARCHIVE_STATUS *status);

#if !defined(_WIN32) && !defined(__APPLE__)
int pyi_utils_replace_process(const char *thisfile, const int argc, char *const argv[]);
#endif

/* Argument handling */
int pyi_utils_initialize_args(const int argc, char *const argv[]);
void pyi_utils_get_args(int *argc, char ***argv);
void pyi_utils_free_args();

/* Apple event handling */
#if defined(__APPLE__) && defined(WINDOWED)
/*
 * Watch for OpenDocument AppleEvents and add the files passed in to the
 * sys.argv command line on the Python side.
 *
 * This allows on Mac OS X to open files when a file is dragged and dropped
 * on the App icon in the OS X dock.
 */
void pyi_process_apple_events(bool short_timeout);
#endif  /* defined(__APPLE__) && defined(WINDOWED) */

/* Magic pattern matching */
extern const unsigned char MAGIC_BASE[8];
uint64_t pyi_utils_find_magic_pattern(FILE *fp, const unsigned char *magic, size_t magic_len);

#endif  /* HEADER_PY_UTILS_H */
