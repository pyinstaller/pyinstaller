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
 * Extraction of dependencies found in MERGE multi-package builds.
 */
#ifndef PYI_MULTIPKG_H
#define PYI_MULTIPKG_H

struct PYI_CONTEXT;
struct ARCHIVE;

/* Maximum number of allowed archives in multi-package archive pool. */
#define PYI_MULTIPKG_ARCHIVE_POOL_SIZE 20

int pyi_multipkg_split_dependency_string(char *path, char *filename, const char *dependency_string);
int pyi_multipkg_extract_dependency(struct PYI_CONTEXT *pyi_ctx, struct ARCHIVE **archive_pool, const char *other_executable, const char *dependency_name, const char *output_filename);

#endif /* PYI_MULTIPKG_H */

