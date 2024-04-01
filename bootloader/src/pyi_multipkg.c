/*
 * ****************************************************************************
 * Copyright (c) 2013-2023, PyInstaller Development Team.
 *
 * Distributed under the terms of the GNU General Public License (version 2
 * or later) with exception for distributing the bootloader.
 *
 * The full license is in the file COPYING.txt, distributed with this software.
 *
 * SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
 * ****************************************************************************
 */

/*
 * Extraction of dependencies found in MERGE multi-package builds.
 */
#include <stdarg.h>
#include <stdio.h> /* vsnprintf */
#include <string.h> /* strcpy */

#include "pyi_multipkg.h"
#include "pyi_archive.h"
#include "pyi_path.h"
#include "pyi_utils.h"


/* Constructs the file path from given components and checks that the path exists.
 * Returns true (1) if it exists, false (0) otherwise. Returns -1 on error. */
/* NOTE: must be visible outside of this unit (i.e., non-static) due to tests! */
int
_format_and_check_path(char *path, const char *fmt, ...)
{
    va_list args;

    va_start(args, fmt);
    if (vsnprintf(path, PATH_MAX, fmt, args) >= PATH_MAX) {
        return -1;
    };
    va_end(args);

    return pyi_path_exists(path);
}

/* Splits the item in the form path:filename. The first part is the path
 * to the other executable (which contains the dependency); the path is
 * relative to the current executable. The second part is the filename of
 * dependency, relative to the top-level application directory. */
/* NOTE: must be visible outside of this unit (i.e., non-static) due to tests! */
int
_split_dependency_name(char *path, char *filename, const char *dependency_name)
{
    char *p;

    /* Copy directly into destination buffer and manipulate there, */
    if (snprintf(path, PATH_MAX, "%s", dependency_name) >= PATH_MAX) {
        return -1;
    }

    p = strchr(path, ':');
    if (p == NULL) {
        return -1; /* no colon in string */
    }
    p[0] ='\0'; /* Terminate path part */

    /* `path` fits into PATH_MAX, so will all substrings. */
    strcpy(filename, ++p);
    if (path[0] == 0 || filename[0] == 0) {
        return -1;
    }

    return 0;
}


/*
 * Look for the archive identified by path in the archive pool.
 *
 * If the archive is found, the pointer to the associated archive is
 * returned; otherwise, the archive is opened and added to the pool,
 * and then returned. If an error occurs, returns NULL.
 */
static ARCHIVE_STATUS *
_get_archive(PYI_CONTEXT *pyi_ctx, ARCHIVE_STATUS **archive_pool, const char *archive_filename)
{
    ARCHIVE_STATUS *archive = NULL;
    int index = 0;

    VS("LOADER: retrieving archive for path %s.\n", archive_filename);

    for (index = 0; archive_pool[index] != NULL; index++) {
        if (strcmp(archive_pool[index]->archivename, archive_filename) == 0) {
            VS("LOADER: archive found in pool: %s\n", archive_filename);
            return archive_pool[index];
        }
    }

    /* Enforce maximum pool size */
    if (index >= PYI_MULTIPKG_ARCHIVE_POOL_SIZE) {
        FATALERROR("Maximum archive pool size reached!");
        return NULL;
    }

    VS("LOADER: archive not found in pool. Creating new entry...\n");

    archive = pyi_arch_status_new();
    if (archive == NULL) {
        return NULL;
    }

    /* TODO: clean this up once we remove the variables */
    if (snprintf(archive->archivename, PATH_MAX, "%s", archive_filename) >= PATH_MAX) {
        FATALERROR("Archive path exceeds PATH_MAX\n");
        pyi_arch_status_free(archive);
        return NULL;
    }

    if (pyi_arch_open(archive)) {
        FATALERROR("Failed to open archive %s!\n", archive_filename);
        pyi_arch_status_free(archive);
        return NULL;
    }

    /* Store in the pool */
    archive_pool[index] = archive;
    return archive;
}

/* Decide if the dependency identified by item is in a onedir or onfile archive
 * and extract it using the appropriate helpers. */
int
pyi_multipkg_extract_dependency(PYI_CONTEXT *pyi_ctx, ARCHIVE_STATUS *archive_pool[], const char *dependency_name)
{
    char other_executable[PATH_MAX];
    char other_executable_dir[PATH_MAX];
    char filename[PATH_MAX];
    char this_executable_dir[PATH_MAX];
    char full_srcpath[PATH_MAX];

    const char *contents_directory;
    int ret;

    VS("LOADER: processing dependency reference: %s\n", dependency_name);

    /* Dependency reference consists of two parts, separated by a colon, for example
     *   (../)other_program:path/to/file
     * if other_program is a onefile executable, or
     *   (../)other_program/other_program:path/to/file
     * if other_program is a onefile executable.
     *
     * The first part is path to the other executable (which contains the dependency),
     * relative to the current executable. On Windows, the executable name does NOT
     * contain .exe suffix. The second part is the filename of dependency, relative to
     * the top-level application directory.
     */
    if (_split_dependency_name(other_executable, filename, dependency_name) == -1) {
        return -1;
    }

    /* Determine parent directories of this executable (absolute path) and the other
     * executable (relative to this executable). If executables are co-located
     * (e.g., two onefile builds), the other executable's parent directory will be ".".
     */
    pyi_path_dirname(this_executable_dir, pyi_ctx->executable_filename);
    pyi_path_dirname(other_executable_dir, other_executable);

    /* Retrieve contents-directory setting, from THIS executable, assuming it is
     * the same across all multi-package executables. In practice, this should matter
     * only if multi-package involves onedir builds.
     */
    contents_directory = pyi_arch_get_option(pyi_ctx->archive, "pyi-contents-directory");

    /* If dependency is located in a onedir build, we should be able to find
     * it on the filesystem (accounting for contents sub-directory settings).
     * If dependency is located in a onefile build, we need to look up the
     * executable (or external PKG archive in case of side-loading). As the
     * executable (with embedded or external PKG archive) is also available
     * in onedir builds, we need to first check for the onedir option.
     *
     * Note that the path relations between different programs in a multipackage
     * should already be handled by the path encoded in the reference, and thus
     * reflected in the `other_executable_dir`:
     *  - for a onefile program referencing a dependency in a onefile program,
     *    it is "."
     *  - for a onedir program referencing a dependency in a onefile program,
     *    it is ".."
     *  - for a onefile program referencing a dependency in a onedir program,
     *    it is "other_program"
     *  - for a onedir program referencing a dependency in a onedir program,
     *    it is "../other_program"
     */
    if (contents_directory) {
        ret = _format_and_check_path(full_srcpath, "%s%c%s%c%s%c%s", this_executable_dir, PYI_SEP, other_executable_dir, PYI_SEP, contents_directory, PYI_SEP, filename);
    } else {
        ret = _format_and_check_path(full_srcpath, "%s%c%s%c%s", this_executable_dir, PYI_SEP, other_executable_dir, PYI_SEP, filename);
    }
    if (ret == true) {
        VS("LOADER: file %s found on filesystem (%s), assuming onedir reference.\n", filename, full_srcpath);
        if (pyi_copy_file(full_srcpath, pyi_ctx->application_home_dir, filename) == -1) {
            FATALERROR("Failed to copy file %s from %s!\n", filename, full_srcpath);
            return -1;
        }
    } else {
        ARCHIVE_STATUS *other_archive = NULL;
        char other_archive_path[PATH_MAX];
        const TOC *toc_entry;

        VS("LOADER: file %s not found on filesystem, assuming onefile reference.\n", filename);

        /* First check for the presence of external .pkg archive, located
         * next to the executable, to account for side-loading mode. */
        if (_format_and_check_path(other_archive_path, "%s%c%s.pkg", this_executable_dir, PYI_SEP, other_executable) != true &&
            _format_and_check_path(other_archive_path, "%s%c%s.exe", this_executable_dir, PYI_SEP, other_executable) != true &&
            _format_and_check_path(other_archive_path, "%s%c%s", this_executable_dir, PYI_SEP, other_executable) != true) {
            FATALERROR("Referenced dependency archive %s not found.\n", other_executable);
            return -1;
        }

        /* Retrieve the referenced archive */
        if ((other_archive = _get_archive(pyi_ctx, archive_pool, other_archive_path)) == NULL) {
            FATALERROR("Failed to open referenced dependency archive %s.\n", other_archive_path);
            return -1;
        }

        /* NOTE: on errors in subsequent calls, do not free the `other_archive`,
         * because its pointer is stored in the archive pool that is cleaned up
         * by the caller! */

        /* Look-up entry in archive's TOC */
        toc_entry = pyi_arch_find_by_name(other_archive, filename);
        if (toc_entry == NULL) {
            FATALERROR("Dependency %s not found in the referenced dependency archive.\n", filename, other_archive_path);
            return -1; /* Entry not found */
        }

        /* Extract */
        if (pyi_arch_extract2fs(other_archive, toc_entry, pyi_ctx->application_home_dir) < 0) {
            FATALERROR("Failed to extract %s from referenced dependency archive %s.\n", filename, other_archive_path);
            return -1;
        }
    }

    return 0;
}
