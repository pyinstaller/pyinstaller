/*
 * ****************************************************************************
 * Copyright (c) 2013, PyInstaller Development Team.
 * Distributed under the terms of the GNU General Public License with exception
 * for distributing bootloader.
 *
 * The full license is in the file COPYING.txt, distributed with this software.
 * ****************************************************************************
 */


#ifndef UTILS_H
#define UTILS_H


#ifdef WIN32
int CreateActContext(char *workpath, char *thisfile);
void ReleaseActContext(void);
#endif


#endif /* UTILS_H */
