/*
 * ****************************************************************************
 * Copyright (c) 2015-2020, PyInstaller Development Team.
 *
 * Distributed under the terms of the GNU General Public License (version 2
 * or later) with exception for distributing the bootloader.
 *
 * The full license is in the file COPYING.txt, distributed with this software.
 *
 * SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
 * ****************************************************************************
 */

#ifndef PYI_PYTHON27_COMPAT_H
#define PYI_PYTHON27_COMPAT_H

#include "pyi_python.h"

extern bool is_py2;  /* true if we are loading Python 2.x library */

void PI_Py2_SetPythonHome(char * str);
void PI_Py2_SetProgramName(char * str);
void PI_Py2Sys_SetPath(char * str);
int  PI_Py2Sys_SetArgvEx(int argc, char ** argv, int updatepath);
void PI_Py2Sys_AddWarnOption(char * str);

#endif  /* PYI_PYTHON27_COMPAT_H */
