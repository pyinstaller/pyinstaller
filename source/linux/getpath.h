/*
 * A special version for minimal installs, where
 * the bootstrap path is the directory in which
 * the executable lives.
 *
 * Copyright (C) 2007, Daniele Varrazzo
 * Based on previous work under copyright (c) 2002 McMillan Enterprises, Inc.
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; either version 2
 * of the License, or (at your option) any later version.
 *
 * In addition to the permissions in the GNU General Public License, the
 * authors give you unlimited permission to link or embed the compiled
 * version of this file into combinations with other programs, and to
 * distribute those combinations without any restriction coming from the
 * use of this file. (The General Public License restrictions do apply in
 * other respects; for example, they cover modification of the file, and
 * distribution when not linked into a combine executable.)
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA
 */

#ifndef PI_GETPATH_H
#define PI_GETPATH_H

void PI_SetProgramName(char *pn);
char *PI_GetProgramName(void);
char *PI_GetPath(void);
char *PI_GetPrefix(void);
char *PI_GetExecPrefix(void);
char *PI_GetProgramFullPath(void);

#endif /* PI_GETPATH_H */
