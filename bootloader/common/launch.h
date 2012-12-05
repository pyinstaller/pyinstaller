/*
 * Launch a python module from an archive.
 *
 * Copyright (C) 2005, Giovanni Bajo
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
#ifndef LAUNCH_H
#define LAUNCH_H


/*****************************************************************
 * The following 4 entries are for applications which may need to
 * use to 2 steps to execute
 *****************************************************************/

/**
 * Initialize the paths and open the archive
 *
 * @param archivePath  The path (with trailing backslash) to the archive.
 *
 * @param archiveName  The file name of the archive, without a path.
 *
 * @param workpath     The path (with trailing backslash) to where
 *                     the binaries were extracted. If they have not
 *                     benn extracted yet, this is NULL. If they have,
 *                     this will either be archivePath, or a temp dir
 *                     where the user has write permissions.
 *
 * @return 0 on success, non-zero otherwise.
 */
int init(ARCHIVE_STATUS *status, char const * archivePath, char  const * archiveName);

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


#endif

