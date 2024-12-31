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
 * Launch a python module from an archive and other related stuff.
 */
#ifndef PYI_LAUNCH_H
#define PYI_LAUNCH_H

struct PYI_CONTEXT;

/*
 * Extract files from embedded archive (onefile mode).
 */
int pyi_launch_extract_files_from_archive(struct PYI_CONTEXT *pyi_ctx);

/*
 * Wrapped platform specific initialization before loading Python and executing
 * all scripts in the archive.
 */
void pyi_launch_initialize(struct PYI_CONTEXT *pyi_ctx);

/*
 * Wrapped platform specific finalization before loading Python and executing
 * all scripts in the archive.
 */
void pyi_launch_finalize(struct PYI_CONTEXT *pyi_ctx);

/*
 * Load Python and execute all scripts in the archive
 *
 * @return -1 for internal failures, or the rc of the last script.
 */
int pyi_launch_execute(struct PYI_CONTEXT *pyi_ctx);


#endif /* PYI_LAUNCH_H */
