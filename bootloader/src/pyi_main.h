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

#include "pyi_global.h"

typedef struct _archive_status ARCHIVE_STATUS;

typedef struct
{
    /* Command line arguments passed to the application */
    int argc;
    char **argv;

    /* Fully resolved path to the executable */
    char executable_filename[PATH_MAX];

    /* Fully resolved path to the main PKG archive */
    char archive_filename[PATH_MAX];

    /* Main PKG archive */
    ARCHIVE_STATUS *archive;
} PYI_CONTEXT;

extern PYI_CONTEXT *global_pyi_ctx;


int pyi_main(PYI_CONTEXT *pyi_ctx);
