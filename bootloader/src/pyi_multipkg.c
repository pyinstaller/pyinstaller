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
#include "pyi_main.h"
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
    if (vsnprintf(path, PYI_PATH_MAX, fmt, args) >= PYI_PATH_MAX) {
        return -1;
    };
    va_end(args);

    return pyi_path_exists(path);
}

/* Splits the dependency string in the form path:filename. The first part
 * is the path to the other executable (which contains the dependency);
 * the path is relative to the current executable. The second part is the
 * filename of dependency, relative to the top-level application directory. */
int
pyi_multipkg_split_dependency_string(char *path, char *filename, const char *dependency_string)
{
    char *p;

    /* Copy directly into destination buffer and manipulate there, */
    if (snprintf(path, PYI_PATH_MAX, "%s", dependency_string) >= PYI_PATH_MAX) {
        return -1;
    }

    p = strchr(path, ':');
    if (p == NULL) {
        return -1; /* no colon in string */
    }
    p[0] = 0; /* Terminate path part */

    /* `path` fits into PYI_PATH_MAX, so will all substrings. */
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
static struct ARCHIVE *
_get_archive(struct PYI_CONTEXT *pyi_ctx, struct ARCHIVE **archive_pool, const char *archive_filename)
{
    struct ARCHIVE *archive = NULL;
    int index = 0;

    PYI_DEBUG("LOADER: retrieving archive for path %s.\n", archive_filename);

    for (index = 0; archive_pool[index] != NULL; index++) {
        if (strcmp(archive_pool[index]->filename, archive_filename) == 0) {
            PYI_DEBUG("LOADER: archive found in pool: %s\n", archive_filename);
            return archive_pool[index];
        }
    }

    /* Enforce maximum pool size */
    if (index >= PYI_MULTIPKG_ARCHIVE_POOL_SIZE) {
        PYI_ERROR("Maximum archive pool size reached!");
        return NULL;
    }

    PYI_DEBUG("LOADER: archive not found in pool. Creating new entry...\n");

    archive = pyi_archive_open(archive_filename);
    if (archive) {
        /* Store in the pool and return */
        archive_pool[index] = archive;
        return archive;
    }

    PYI_ERROR("Failed to open archive %s!\n", archive_filename);
    return NULL;
}

/* Decide if the dependency identified by item is in a onedir or onfile archive
 * and extract it using the appropriate helpers. */
int
pyi_multipkg_extract_dependency(
    struct PYI_CONTEXT *pyi_ctx,
    struct ARCHIVE **archive_pool,
    const char *other_executable,
    const char *dependency_name,
    const char *output_filename
)
{
    char other_executable_dir[PYI_PATH_MAX];
    char this_executable_dir[PYI_PATH_MAX];
    char full_srcpath[PYI_PATH_MAX];
    int ret;

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
     *
     * This implementation assumes that the dependency name from the TOC entry has
     * already been split by the caller, using `pyi_multipkg_split_dependency_name`,
     * and that results have been passed via `other_executable` and `dependency_name`
     * arguments.
     */

    PYI_DEBUG("LOADER: processing multi-package reference: %s %s\n", other_executable, dependency_name);

    /* Determine parent directories of this executable (absolute path) and the other
     * executable (relative to this executable). If executables are co-located
     * (e.g., two onefile builds), the other executable's parent directory will be ".".
     */
    pyi_path_dirname(this_executable_dir, pyi_ctx->executable_filename);
    pyi_path_dirname(other_executable_dir, other_executable);

    /* If dependency is located in a onedir build, we should be able to find
     * it on the filesystem (accounting for contents sub-directory setting
     * of the main archive/executable - assuming they are the same across
     * all executables).
     *
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
    if (pyi_ctx->contents_subdirectory) {
        ret = _format_and_check_path(full_srcpath, "%s%c%s%c%s%c%s", this_executable_dir, PYI_SEP, other_executable_dir, PYI_SEP, pyi_ctx->contents_subdirectory, PYI_SEP, dependency_name);
    } else {
        ret = _format_and_check_path(full_srcpath, "%s%c%s%c%s", this_executable_dir, PYI_SEP, other_executable_dir, PYI_SEP, dependency_name);
    }
    if (ret == true) {
        PYI_DEBUG("LOADER: file %s found on filesystem (%s), assuming onedir reference.\n", dependency_name, full_srcpath);
        if (pyi_copy_file(full_srcpath, output_filename) == -1) {
            PYI_ERROR("Failed to copy file %s from %s!\n", dependency_name, full_srcpath);
            return -1;
        }
    } else {
        struct ARCHIVE *other_archive = NULL;
        char other_archive_path[PYI_PATH_MAX];
        const struct TOC_ENTRY *toc_entry;

        PYI_DEBUG("LOADER: file %s not found on filesystem, assuming onefile reference.\n", dependency_name);

        /* First check for the presence of external .pkg archive, located
         * next to the executable, to account for side-loading mode. */
        if (_format_and_check_path(other_archive_path, "%s%c%s.pkg", this_executable_dir, PYI_SEP, other_executable) != true &&
            _format_and_check_path(other_archive_path, "%s%c%s.exe", this_executable_dir, PYI_SEP, other_executable) != true &&
            _format_and_check_path(other_archive_path, "%s%c%s", this_executable_dir, PYI_SEP, other_executable) != true) {
            PYI_ERROR("Referenced dependency archive %s not found.\n", other_executable);
            return -1;
        }

        /* Retrieve the referenced archive */
        if ((other_archive = _get_archive(pyi_ctx, archive_pool, other_archive_path)) == NULL) {
            PYI_ERROR("Failed to open referenced dependency archive %s.\n", other_archive_path);
            return -1;
        }

        /* NOTE: on errors in subsequent calls, do not free the `other_archive`,
         * because its pointer is stored in the archive pool that is cleaned up
         * by the caller! */

        /* Look-up entry in archive's TOC */
        toc_entry = pyi_archive_find_entry_by_name(other_archive, dependency_name);
        if (toc_entry == NULL) {
            PYI_ERROR("Dependency %s not found in the referenced dependency archive.\n", dependency_name, other_archive_path);
            return -1; /* Entry not found */
        }

        /* Extract */
        if (pyi_archive_extract2fs(other_archive, toc_entry, output_filename) < 0) {
            PYI_ERROR("Failed to extract %s from referenced dependency archive %s.\n", dependency_name, other_archive_path);
            return -1;
        }
    }

    return 0;
}
