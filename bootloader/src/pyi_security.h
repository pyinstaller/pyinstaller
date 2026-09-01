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

bool pyi_security_onefile_parent_verification_available();

bool pyi_security_verify_application_home_dir_name(const struct PYI_CONTEXT *pyi_ctx, unsigned int *onefile_parent_pid);
bool pyi_security_verify_application_home_dir_permissions(const struct PYI_CONTEXT *pyi_ctx);

bool pyi_security_verify_onefile_parent_pid(const struct PYI_CONTEXT *pyi_ctx, const unsigned int onefile_parent_pid, const bool search_process_tree);
bool pyi_security_verify_onefile_parent_executable(const struct PYI_CONTEXT *pyi_ctx, const unsigned int onefile_parent_pid);

#endif /* PYI_SECURITY_H */
