/*
 * ****************************************************************************
 * Copyright (c) 2013-2016, PyInstaller Development Team.
 * Distributed under the terms of the GNU General Public License with exception
 * for distributing bootloader.
 *
 * The full license is in the file COPYING.txt, distributed with this software.
 * ****************************************************************************
 */

/*
 * Path manipulation utilities.
 */

#ifndef PYI_PATH_H
#define PYI_PATH_H

/* Path manipulation. Result is added to the supplied buffer. */
void *pyi_path_basename(char *result, const char *path);
void *pyi_path_dirname(char *result, const char *path);
void *pyi_path_join(char *result, const char *path1, const char *path2);
void *pyi_path_normalize(char *result, const char *path);
int pyi_path_fullpath(char *abs, size_t abs_size, const char *rel);
/* TODO implement. */
/* void *pyi_path_abspath(char *result, const char *path); */

int pyi_path_executable(char *execfile, const char *appname);
void pyi_path_homepath(char *homepath, const char *executable);
void pyi_path_archivefile(char *archivefile, const char *executable);

#ifdef _WIN32
FILE *pyi_path_fopen(const char *filename, const char *mode);
#else
    #define pyi_path_fopen(x, y)    fopen(x, y)
#endif
#define pyi_path_fclose(x)    fclose(x)

#endif  /* PYI_PATH_H */
