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
 * Functions to load, initialize and launch Python.
 */

#ifndef PYI_PYTHONLIB_H
#define PYI_PYTHONLIB_H


int pyi_pylib_attach(ARCHIVE_STATUS *status, int *loadedNew);
int pyi_pylib_load(ARCHIVE_STATUS *status); /* note - pyi_pylib_attach will call this if not already loaded */
int pyi_pylib_start_python(ARCHIVE_STATUS *status, int argc, char *argv[]);
int pyi_pylib_import_modules(ARCHIVE_STATUS *status);
int pyi_pylib_install_zlibs(ARCHIVE_STATUS *status);
int pyi_pylib_run_scripts(ARCHIVE_STATUS *status);

void pyi_pylib_finalize(ARCHIVE_STATUS *status);


#endif /* PYI_PYTHONLIB_H */
