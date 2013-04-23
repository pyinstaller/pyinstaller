/*
 * ****************************************************************************
 * Copyright (c) 2013, PyInstaller Development Team.
 * Distributed under the terms of the GNU General Public License with exception
 * for distributing bootloader.
 *
 * The full license is in the file COPYING.txt, distributed with this software.
 * ****************************************************************************
 */

/*
 * A special version for minimal installs, where
 * the bootstrap path is the directory in which
 * the executable lives.
 */

#ifndef PI_GETPATH_H
#define PI_GETPATH_H

void PI_SetProgramName(const char *pn);
const char *PI_GetProgramName(void);
char *PI_GetPath(void);
char *PI_GetPrefix(void);
char *PI_GetExecPrefix(void);
char *PI_GetProgramFullPath(void);

#endif /* PI_GETPATH_H */
