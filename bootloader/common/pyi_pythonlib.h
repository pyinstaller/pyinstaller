/*
 * Functions to load, initialize and launch Python.
 *
 * Copyright (C) 2012, Martin Zibricky
 * Copyright (C) 2005-2011, Giovanni Bajo
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
#ifndef PYI_PYTHONLIB_H
#define PYI_PYTHONLIB_H


int pyi_pylib_attach(ARCHIVE_STATUS *status, int *loadedNew);
int pyi_pylib_load(ARCHIVE_STATUS *status); /* note - pyi_pylib_attach will call this if not already loaded */
int pyi_pylib_start_python(ARCHIVE_STATUS *status, int argc, char *argv[]);
int pyi_pylib_import_modules(ARCHIVE_STATUS *status);
int pyi_pylib_install_zlibs(ARCHIVE_STATUS *status);
int pyi_pylib_run_scripts(ARCHIVE_STATUS *status);

void pyi_pylib_finalize(void);


#endif /* PYI_PYTHONLIB_H */
