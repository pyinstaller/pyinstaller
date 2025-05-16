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
 * Utility functions.
 */

#ifndef PYI_UTILS_H
#define PYI_UTILS_H

#include <stdio.h> /* FILE */
#include <inttypes.h> /* uint64_t */

struct PYI_CONTEXT;

/* Environment variables. */
char *pyi_getenv(const char *variable);
int pyi_setenv(const char *variable, const char *value);
int pyi_unsetenv(const char *variable);

/* Temporary top-level application directory (onefile). */
int pyi_create_temporary_application_directory(struct PYI_CONTEXT *pyi_ctx);

/* Recursive directory deletion. */
int pyi_recursive_rmdir(const char *dir);

/* Misc. file/directory manipulation. */
int pyi_create_parent_directory_tree(const struct PYI_CONTEXT *pyi_ctx, const char *prefix_path, const char *filename);
int pyi_copy_file(const char *src_filename, const char *dest_filename);

/* Child process */
int pyi_utils_create_child(struct PYI_CONTEXT *pyi_ctx);

#if !defined(_WIN32) && !defined(__APPLE__)
int pyi_utils_set_library_search_path(const char *path);
#endif

/* Argument handling (POSIX only) */
#if !defined(_WIN32)
int pyi_utils_initialize_args(struct PYI_CONTEXT *pyi_ctx, const int argc, char *const argv[]);
int pyi_utils_append_to_args(struct PYI_CONTEXT *pyi_ctx, const char *arg);
void pyi_utils_free_args(struct PYI_CONTEXT *pyi_ctx);
char *const *pyi_prepend_dynamic_loader_to_argv(const int argc, char *const argv[], char *const loader_filename);
#endif

/* Magic pattern matching */
extern const unsigned char MAGIC_BASE[8];
uint64_t pyi_utils_find_magic_pattern(FILE *fp, const unsigned char *magic, size_t magic_len);

/* Security descriptor for temporary directory (Windows only) */
#if defined(_WIN32)
SECURITY_ATTRIBUTES *pyi_win32_initialize_security_descriptor();
void pyi_win32_free_security_descriptor(SECURITY_ATTRIBUTES **security_attr_ref);
#endif

/* Console minimization/hiding (Windows console-enabled build only) */
#if defined(_WIN32) && !defined(WINDOWED)
void pyi_win32_hide_console();
void pyi_win32_minimize_console();
#endif

/* Attempt to mitigate locked files in temporary directory that prevent its removal. */
#if defined(_WIN32)
int pyi_win32_mitigate_locked_temporary_directory(const struct PYI_CONTEXT *pyi_ctx);
#endif

/* Windows low-level helpers */
#ifdef _WIN32

char *pyi_win32_wcs_to_utf8(const wchar_t *src, char *dest, size_t buflen);
wchar_t *pyi_win32_utf8_to_wcs(const char *src, wchar_t *dest, size_t buflen);

int pyi_win32_is_symlink(const wchar_t *path);

int pyi_win32_realpath(const wchar_t *path, wchar_t *resolved_path);

int pyi_win32_is_drive_root(const wchar_t *path);

#endif /* _WIN32 */


#endif /* PYI_UTILS_H */
