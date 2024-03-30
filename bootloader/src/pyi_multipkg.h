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

#include "pyi_main.h"


/* Maximum number of allowed archives in multi-package archive pool. */
#define PYI_MULTIPKG_ARCHIVE_POOL_SIZE 20

/* Extract depdencency */
int pyi_multipkg_extract_dependency(PYI_CONTEXT *pyi_ctx, ARCHIVE_STATUS *archive_pool[], const char *dependency_name);


#endif  /* PYI_MULTIPKG_H */

