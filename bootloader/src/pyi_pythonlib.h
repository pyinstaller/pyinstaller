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
 * Functions to load, initialize and launch Python.
 */

#ifndef PYI_PYTHONLIB_H
#define PYI_PYTHONLIB_H

struct PYI_CONTEXT;

int pyi_pylib_load(struct PYI_CONTEXT *pyi_ctx);
int pyi_pylib_start_python(const struct PYI_CONTEXT *pyi_ctx);
int pyi_pylib_import_modules(const struct PYI_CONTEXT *pyi_ctx);
int pyi_pylib_install_pyz(const struct PYI_CONTEXT *pyi_ctx);
int pyi_pylib_run_scripts(const struct PYI_CONTEXT *pyi_ctx);

void pyi_pylib_finalize(const struct PYI_CONTEXT *pyi_ctx);

#endif /* PYI_PYTHONLIB_H */
