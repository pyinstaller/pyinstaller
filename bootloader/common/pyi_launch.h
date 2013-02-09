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
 * Launch a python module from an archive.
 */
#ifndef PYI_LAUNCH_H
#define PYI_LAUNCH_H


/*****************************************************************
 * The following 4 entries are for applications which may need to
 * use to 2 steps to execute
 *****************************************************************/

/**
 * Extract binaries in the archive
 *
 * @param workpath     (OUT) Where the binaries were extracted to. If
 *                      none extracted, is NULL.
 *
 * @return 0 on success, non-zero otherwise.
 */
int extractBinaries(ARCHIVE_STATUS *status_list[]);

/*
 * Check if binaries need to be extracted. If not, this is probably a onedir
 * solution, and a child process will not be required on windows.
 */
int needToExtractBinaries(ARCHIVE_STATUS *status_list[]);

/**
 * Load Python and execute all scripts in the archive
 *
 * @param argc			Count of "commandline" args
 *
 * @param argv			The "commandline".
 *
 * @return -1 for internal failures, or the rc of the last script.
 */
int doIt(ARCHIVE_STATUS *status, int argc, char *argv[]);

/*
 * Call a simple "int func(void)" entry point.  Assumes such a function
 * exists in the main namespace.
 * Return non zero on failure, with -2 if the specific error is
 * that the function does not exist in the namespace.
 *
 * @param name		Name of the function to execute.
 * @param presult	Integer return value.
 */
int callSimpleEntryPoint(char *name, int *presult);

/**
 * Clean up extracted binaries
 */
void cleanUp(ARCHIVE_STATUS *status);


#endif  /* PYI_LAUNCH_H */

