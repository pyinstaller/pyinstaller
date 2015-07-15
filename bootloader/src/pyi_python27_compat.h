/*
 * ****************************************************************************
 * Copyright (c) 2015, PyInstaller Development Team.
 * Distributed under the terms of the GNU General Public License with exception
 * for distributing bootloader.
 *
 * The full license is in the file COPYING.txt, distributed with this software.
 * ****************************************************************************
 */

#ifndef PYI_PYTHON27_COMPAT_H
#define PYI_PYTHON27_COMPAT_H

#include "pyi_python.h"

bool is_py2; // true if we are loading Python 2.x library

inline void PI_Py2_SetPythonHome(char * str);
inline void PI_Py2_SetProgramName(char * str);
inline void PI_Py2Sys_SetPath(char * str);
inline int  PI_Py2Sys_SetArgvEx(int argc, char ** argv, int updatepath);
inline void PI_Py2Sys_AddWarnOption(char * str);

#endif /* PYI_PYTHON27_COMPAT_H */
