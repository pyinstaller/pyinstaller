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
 * Utility functions. This file contains implementations that are common
 * to all platforms/OSes.
 */

#include <stdio.h>

#ifdef _WIN32
    #include <windows.h>
#else
    #include <stdlib.h>
    #include <unistd.h>
    #include <sys/stat.h>
#endif

#include <string.h>

/* PyInstaller headers. */
#include "pyi_utils.h"

#include "pyi_main.h"
#include "pyi_path.h"


/**********************************************************************\
 *                    Misc. file/directory helpers                    *
\**********************************************************************/
/*
 * Helper that creates parent directory tree for the given filename,
 * rooted under the given prefix path. The prefix path is assumed to
 * already exist.
 *
 * Returns 0 on success, -1 on failure.
 */
int
pyi_create_parent_directory_tree(const struct PYI_CONTEXT *pyi_ctx, const char *prefix_path, const char *filename)
{
    char path[PYI_PATH_MAX];
    char *subpath_cursor;
    size_t path_length;

    /* Ensure that combined path length does not exceed max path. */
    if (strlen(prefix_path) + strlen(filename) + 1 >= PYI_PATH_MAX) {
        return -1;
    }

    /* Write prefix path, append separator, and store length; so we
     * can keep appending sub-paths at the end */
    path_length = snprintf(path, PYI_PATH_MAX, "%s%c", prefix_path, PYI_SEP);

    /* Process directory components in filename */
    for (subpath_cursor = strchr(filename, PYI_SEP); subpath_cursor != NULL; subpath_cursor = strchr(++subpath_cursor, PYI_SEP)) {
        int subpath_length = (int)(subpath_cursor - filename);

        snprintf(path + path_length, PYI_PATH_MAX - path_length, "%.*s", subpath_length, filename);

        /* Create path if necessary */
        if (pyi_path_exists(path) == 0) {
#ifdef _WIN32
            wchar_t path_w[PYI_PATH_MAX];
            pyi_win32_utf8_to_wcs(path, path_w, PYI_PATH_MAX);

            /* CreateDirectoryW returns 0 on failure. */
            if (CreateDirectoryW(path_w, pyi_ctx->security_attr) == 0) {
                return -1;
            }
#else
            if (mkdir(path, 0700) < 0) {
                return -1;
            }
#endif
        }
    }

    return 0;
}

/*
 * Copy the source file to destination, in chunkc of 4 kB. The parent
 * directory tree of the destination must file must already exist
 */
int
pyi_copy_file(const char *src_filename, const char *dest_filename)
{
    FILE *fp_in;
    FILE *fp_out ;
    char buffer[4096];
    size_t byte_count = 0;
    int error = 0;

    fp_in = pyi_path_fopen(src_filename, "rb");
    if (fp_in == NULL) {
        return -1;
    }

    fp_out = pyi_path_fopen(dest_filename, "wb");
    if (fp_out == NULL) {
        fclose(fp_in);
        return -1;
    }

    while (!feof(fp_in)) {
        /* Read chunk */
        byte_count = fread(buffer, 1, 4096, fp_in);
        if (byte_count <= 0) {
            /* No data left or error */
            if (ferror(fp_in)) {
                clearerr(fp_in);
                error = -1;
            }
            break;
        }

        /* Write chunk */
        byte_count = fwrite(buffer, 1, byte_count, fp_out);
        if (byte_count <= 0 || ferror(fp_out)) {
            clearerr(fp_out);
            error = -1;
            break;
        }
    }

    /* Copy permissions bits */
#ifndef WIN32
    if (1) {
        struct stat stat_buf;
        mode_t permissions;

        /* Always set user readable and user writable, and copy the rest
         * from the source file */
        permissions = S_IRUSR | S_IWUSR;
        if (stat(src_filename, &stat_buf) == 0) {
            permissions |= stat_buf.st_mode;
        }
        fchmod(fileno(fp_out), permissions);
    }
#endif

    fclose(fp_in);
    fclose(fp_out);

    return error;
}


/**********************************************************************\
 *                       Magic pattern scanning                       *
\**********************************************************************/
/*
 * The base for MAGIC pattern(s) used within the bootloader. The actual
 * pattern should be programmatically constructed by copying this
 * array to a buffer and adjusting the fourth byte. This way, we avoid
 * storing the actual pattern in the executable, which would produce
 * false-positive matches when the executable is scanned.
 */
const unsigned char MAGIC_BASE[8] = {
    'M', 'E', 'I', 000,
    013, 012, 013, 016
};

/*
 * Perform full back-to-front scan of the given file and search for the
 * specified MAGIC pattern.
 *
 * Returns offset within the file if MAGIC pattern is found, 0 otherwise.
 */
uint64_t
pyi_utils_find_magic_pattern(FILE *fp, const unsigned char *magic, size_t magic_len)
{
    static const int SEARCH_CHUNK_SIZE = 8192;
    unsigned char *buffer = NULL;
    uint64_t start_pos, end_pos;
    uint64_t offset = 0;  /* return value */

    /* Allocate the read buffer */
    buffer = malloc(SEARCH_CHUNK_SIZE);
    if (!buffer) {
        PYI_DEBUG("LOADER: failed to allocate read buffer (%d bytes)!\n", SEARCH_CHUNK_SIZE);
        goto cleanup;
    }

    /* Determine file size */
    if (pyi_fseek(fp, 0, SEEK_END) < 0) {
        PYI_DEBUG("LOADER: failed to seek to the end of the file!\n");
        goto cleanup;
    }
    end_pos = pyi_ftell(fp);

    /* Sanity check */
    if (end_pos < magic_len) {
        PYI_DEBUG("LOADER: file is too short to contain magic pattern!\n");
        goto cleanup;
    }

    /* Search the file back to front, in overlapping SEARCH_CHUNK_SIZE
     * chunks. */
    do {
        size_t chunk_size, i;
        start_pos = (end_pos >= SEARCH_CHUNK_SIZE) ? (end_pos - SEARCH_CHUNK_SIZE) : 0;
        chunk_size = (size_t)(end_pos - start_pos);

        /* Is the remaining chunk large enough to hold the pattern? */
        if (chunk_size < magic_len) {
            break;
        }

        /* Read the chunk */
        if (pyi_fseek(fp, start_pos, SEEK_SET) < 0) {
            PYI_DEBUG("LOADER: failed to seek to the offset 0x%" PRIX64 "!\n", start_pos);
            goto cleanup;
        }
        if (fread(buffer, 1, chunk_size, fp) != chunk_size) {
            PYI_DEBUG("LOADER: failed to read chunk (%zd bytes)!\n", chunk_size);
            goto cleanup;
        }

        /* Scan the chunk */
        for (i = chunk_size - magic_len + 1; i > 0; i--) {
            if (memcmp(buffer + i -1, magic, magic_len) == 0) {
                offset = start_pos + i - 1;
                goto cleanup;
            }
        }

        /* Adjust search location for next chunk; ensure proper overlap */
        end_pos = start_pos + magic_len - 1;
    } while (start_pos > 0);

cleanup:
    free(buffer);

    return offset;
}
