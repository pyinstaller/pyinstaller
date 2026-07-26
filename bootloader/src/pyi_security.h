/*
 * ****************************************************************************
 * Copyright (c) 2026, PyInstaller Development Team.
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
 * Additional security verification of inherited run-time environment.
 */


#ifndef PYI_SECURITY_H
#define PYI_SECURITY_H

struct PYI_CONTEXT;

int pyi_security_verify_parent_proces(const struct PYI_CONTEXT *pyi_ctx);
int pyi_security_verify_application_home_dir(const struct PYI_CONTEXT *pyi_ctx);

#endif /* PYI_SECURITY_H */
