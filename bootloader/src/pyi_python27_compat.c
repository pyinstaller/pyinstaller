/*
 * ****************************************************************************
 * Copyright (c) 2015, PyInstaller Development Team.
 * Distributed under the terms of the GNU General Public License with exception
 * for distributing bootloader.
 *
 * The full license is in the file COPYING.txt, distributed with this software.
 * ****************************************************************************
 */

#include "pyi_python.h"

/*
This file implements Python 2.7 compatible wrappers for functions
expecting "char *" here their Python3-counter-part expects "wchar_t *".
The trick as that the function names are the same for Python 2 and
Python 3 (only the argument type differs) and are loaded dynamically.
*/

inline void PI_Py2_SetPythonHome(char * str) {
  PI_Py_SetPythonHome((wchar_t *) str);
};

inline void PI_Py2_SetProgramName(char * str) {
  PI_Py_SetProgramName((wchar_t *) str);
};

inline void PI_Py2Sys_SetPath(char * str) {
  PI_PySys_SetPath((wchar_t *) str);
};

inline int PI_Py2Sys_SetArgvEx(int argc, char ** argv, int updatepath) {
  return PI_PySys_SetArgvEx(argc, (wchar_t **) argv, updatepath);
};

inline void PI_Py2Sys_AddWarnOption(char * str) {
  PI_PySys_AddWarnOption((wchar_t *) str);
};
bool is_py2; // true if we are loading Python 2.x library
