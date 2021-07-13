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
 * Launch a python module from an archive and other related stuff.
 */
#ifndef PYI_LAUNCH_H
#define PYI_LAUNCH_H

#include "pyi_archive.h"
#include "pyi_splash.h"

/*****************************************************************
* The following 4 entries are for applications which may need to
* use to 2 steps to execute
*****************************************************************/

/*
 * Extract binaries from the archive
 *
 * @param archive_status     The archive from which the binaries will
 *                           be extracted.
 *
 * @param splash_status      The splash screen status which describes
 *                           on which progress updated to occur. May
 *                           be NULL
 *
 * @return 0 on success, non-zero otherwise.
 */
int pyi_launch_extract_binaries(ARCHIVE_STATUS *archive_status,
                                SPLASH_STATUS *splash_status);

/*
 * Check if binaries need to be extracted. If not, this is probably a onedir
 * solution, and a child process will not be required on windows.
 */
int pyi_launch_need_to_extract_binaries(ARCHIVE_STATUS *archive_status);

/*
 * Wrapped platform specific initialization before loading Python and executing
 * all scripts in the archive.
 */
void pyi_launch_initialize(ARCHIVE_STATUS *archive_status);

/*
 * Wrapped platform specific finalization before loading Python and executing
 * all scripts in the archive.
 */
void pyi_launch_finalize(ARCHIVE_STATUS *archive_status);

/*
 * Load Python and execute all scripts in the archive
 *
 * @return -1 for internal failures, or the rc of the last script.
 */
int pyi_launch_execute(ARCHIVE_STATUS *status);

/*
 * Transform parent process to background (OSX only).
 */
void pyi_parent_to_background();

#endif  /* PYI_LAUNCH_H */

