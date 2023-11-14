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
 * Functions related to PyInstaller archive embedded in executable.
 */

#include <stdio.h>
#include <stddef.h>  /* ptrdiff_t */
#include <stdlib.h>  /* malloc */
#include <string.h>  /* strncmp, strcpy, strcat */
#include <sys/stat.h>  /* fchmod */

/* PyInstaller headers. */
#include "zlib.h"
#include "pyi_global.h"
#include "pyi_path.h"
#include "pyi_archive.h"
#include "pyi_utils.h"
#include "pyi_python.h"

int pyvers = 0;

/*
 * Return pointer to the next TOC entry.
 */
const TOC *
pyi_arch_increment_toc_ptr(const ARCHIVE_STATUS *status, const TOC *ptoc)
{
    return (const TOC *)((const char *)ptoc + ptoc->structlen);
}


/*
 * Helper for pyi_arch_extract/pyi_arch_extract2fs that extracts a
 * compressed file from the archive, and writes it into the provided
 * file handle or data buffer. Exactly one of out_fp or out_ptr needs
 * to be valid.
 */
static int
_pyi_arch_extract_compressed(FILE *archive_fp, const TOC *ptoc, FILE *out_fp, unsigned char *out_ptr)
{
    const size_t CHUNK_SIZE = 8192;
    unsigned char *buffer_in = NULL;
    unsigned char *buffer_out = NULL;
    uint64_t remaining_size;
    z_stream zstream;
    int rc = -1;

    /* Allocate and initialize inflate state */
    zstream.zalloc = Z_NULL;
    zstream.zfree = Z_NULL;
    zstream.opaque = Z_NULL;
    zstream.avail_in = 0;
    zstream.next_in = Z_NULL;
    rc = inflateInit(&zstream);
    if (rc != Z_OK) {
        FATALERROR("Failed to extract %s: inflateInit() failed with return code %d!\n", ptoc->name, rc);
        return -1;
    }

    /* Allocate I/O buffers */
    buffer_in = (unsigned char *)malloc(CHUNK_SIZE);
    if (buffer_in == NULL) {
        FATAL_PERROR("malloc", "Failed to extract %s: failed to allocate temporary input buffer!\n", ptoc->name);
        goto cleanup;
    }
    buffer_out = (unsigned char *)malloc(CHUNK_SIZE);
    if (buffer_out == NULL) {
        FATAL_PERROR("malloc", "Failed to extract %s: failed to allocate temporary output buffer!\n", ptoc->name);
        goto cleanup;
    }

    /* Decompress until deflate stream ends or end of file is reached */
    remaining_size = ptoc->len;
    do {
        /* Read chunk to input buffer */
        size_t chunk_size = (CHUNK_SIZE < remaining_size) ? CHUNK_SIZE : (size_t)remaining_size;
        if (fread(buffer_in, 1, chunk_size, archive_fp) != chunk_size || ferror(archive_fp)) {
            rc = -1;
            goto cleanup;
        }
        remaining_size -= chunk_size;

        /* Run inflate() on input until output buffer is not full. */
        zstream.avail_in = (uInt)chunk_size;
        zstream.next_in = buffer_in;
        do {
            size_t out_len;
            zstream.avail_out = (uInt)CHUNK_SIZE;
            zstream.next_out = buffer_out;
            rc = inflate(&zstream, Z_NO_FLUSH);
            switch (rc) {
                case Z_NEED_DICT:
                    rc = Z_DATA_ERROR; /* and fall through */
                case Z_DATA_ERROR:
                case Z_MEM_ERROR:
                case Z_STREAM_ERROR:
                    goto decompress_end;
            }
            /* Copy the extracted data */
            out_len = CHUNK_SIZE - zstream.avail_out;
            if (out_fp) {
                /* Write to output file */
                if (fwrite(buffer_out, 1, out_len, out_fp) != out_len || ferror(out_fp)) {
                    rc = Z_ERRNO;
                    goto decompress_end;
                }
            } else if (out_ptr) {
                /* Copy to output data buffer */
                memcpy(out_ptr, buffer_out, out_len);
                out_ptr += out_len;
            }
        } while (zstream.avail_out == 0);
        /* Done when inflate() says it's done */
    } while (rc != Z_STREAM_END && remaining_size > 0);

decompress_end:
    if (rc == Z_STREAM_END) {
        rc = 0; /* Success */
    } else {
        FATALERROR("Failed to extract %s: decompression resulted in return code %d!\n", ptoc->name, rc);
        rc = -1;
    }

cleanup:
    inflateEnd(&zstream);
    free(buffer_in);
    free(buffer_out);

    return rc;
}

/*
 * Helper for pyi_arch_extract2fs that extracts an uncompressed file from
 * the archive into the provided file handle.
 */
static int
_pyi_arch_extract2fs_uncompressed(FILE *archive_fp, const TOC *ptoc, FILE *out_fp)
{
    const size_t CHUNK_SIZE = 8192;
    unsigned char *buffer;
    uint64_t remaining_size;
    int rc = 0;

    /* Allocate temporary buffer for a single chunk */
    buffer = (unsigned char *)malloc(CHUNK_SIZE);
    if (buffer == NULL) {
        FATAL_PERROR("malloc", "Failed to extract %s: failed to allocate temporary buffer!\n", ptoc->name);
        return -1;
    }

    /* ... and copy it, chunk by chunk */
    remaining_size = ptoc->ulen;
    while (remaining_size > 0) {
        size_t chunk_size = (CHUNK_SIZE < remaining_size) ? CHUNK_SIZE : (size_t)remaining_size;
        if (fread(buffer, chunk_size, 1, archive_fp) < 1) {
            FATAL_PERROR("fread", "Failed to extract %s: failed to read data chunk!\n", ptoc->name);
            rc = -1;
            break;
        }
        if (fwrite(buffer, chunk_size, 1, out_fp) < 1) {
            FATAL_PERROR("fwrite", "Failed to extract %s: failed to write data chunk!\n", ptoc->name);
            rc = -1;
            break;
        }
        remaining_size -= chunk_size;
    }
    free(buffer);
    return rc;
}

/*
 * Helper for pyi_arch_extract that extracts an uncompressed file from
 * the archive into the provided (pre-allocated) buffer.
 */
static int
_pyi_arch_extract_uncompressed(FILE *archive_fp, const TOC *ptoc, unsigned char *out_buf)
{
    const size_t CHUNK_SIZE = 8192;
    unsigned char *buffer;
    uint64_t remaining_size;

    /* Read the file into buffer, chunk by chunk */
    buffer = out_buf;
    remaining_size = ptoc->ulen;
    while (remaining_size > 0) {
        size_t chunk_size = (CHUNK_SIZE < remaining_size) ? CHUNK_SIZE : (size_t)remaining_size;
        if (fread(buffer, chunk_size, 1, archive_fp) < 1) {
            FATAL_PERROR("fread", "Failed to extract %s: failed to read data chunk!\n", ptoc->name);
            return -1;
        }
        remaining_size -= chunk_size;
        buffer += chunk_size;
    }
    return 0;
}

/*
 * Extract an archive entry into data buffer.
 * Returns pointer to the data (must be freed).
 */
unsigned char *
pyi_arch_extract(const ARCHIVE_STATUS *status, const TOC *ptoc)
{
    FILE *archive_fp = NULL;
    unsigned char *data = NULL;
    int rc = 0;

    /* Open archive (source) file... */
    archive_fp = pyi_path_fopen(status->archivename, "rb");
    if (archive_fp == NULL) {
        FATALERROR("Failed to extract %s: failed to open archive file!\n", ptoc->name);
        return NULL;
    }
    /* ... and seek to the beginning of entry's data */
    if (pyi_fseek(archive_fp, status->pkgstart + ptoc->pos, SEEK_SET) < 0) {
        FATAL_PERROR("fseek", "Failed to extract %s: failed to seek to the entry's data!\n", ptoc->name);
        goto cleanup;
    }

    /* Allocate the data buffer */
    data = (unsigned char *)malloc(ptoc->ulen);
    if (data == NULL) {
        FATAL_PERROR("malloc", "Failed to extract %s: failed to allocate data buffer (%u bytes)!\n", ptoc->name, ptoc->ulen);
        goto cleanup;
    }

    /* Extract */
    if (ptoc->cflag == '\1') {
        rc = _pyi_arch_extract_compressed(archive_fp, ptoc, NULL, data);
    } else {
        rc = _pyi_arch_extract_uncompressed(archive_fp, ptoc, data);
    }
    if (rc != 0) {
        free(data);
        data = NULL;
    }

cleanup:
    fclose(archive_fp);

    return data;
}

/*
 * Create/extract symbolic link from the archive.
 */
static int
pyi_arch_create_symlink(const ARCHIVE_STATUS *status, const TOC *ptoc)
{
    char *link_target = NULL;
    char link_name[PATH_MAX];
    int rc = -1;

    /* Extract symlink target */
    link_target = (char *) pyi_arch_extract(status, ptoc);
    if (!link_target) {
        goto cleanup;
    }

    /* Ensure parent path exists */
    if (pyi_create_parent_directory(status->temppath, ptoc->name) < 0) {
        goto cleanup;
    }

    /* Create the symbolic link */
    if (snprintf(link_name, PATH_MAX, "%s%c%s", status->temppath, PYI_SEP, ptoc->name) >= PATH_MAX) {
        goto cleanup;
    }
    rc = pyi_path_mksymlink(link_target, link_name);

cleanup:
    free(link_target);

    return rc;
}

/*
 * Extract an archive entry into file in the temporary directory.
 * The temporary directory must be initialized via `pyi_arch_create_tempdir`
 * before this function is called.
 */
int
pyi_arch_extract2fs(const ARCHIVE_STATUS *status, const TOC *ptoc)
{
    FILE *archive_fp = NULL;
    FILE *out_fp = NULL;
    int rc = 0;

    /* Temporary directory must be initialized before calling this function */
    if (status->has_temp_directory != true) {
        FATALERROR("pyi_arch_extract2fs was called before temporary directory was initialized!\n");
        return -1;
    }

    /* Handle symbolic links */
    if (ptoc->typcd == ARCHIVE_ITEM_SYMLINK) {
        rc = pyi_arch_create_symlink(status, ptoc);
        if (rc < 0) {
            FATALERROR("Failed to create symbolic link %s!\n", ptoc->name);
        }
        return rc;
    }

    /* Open target file */
    out_fp = pyi_open_target_file(status->temppath, ptoc->name);
    if (out_fp == NULL) {
        FATAL_PERROR("fopen", "Failed to extract %s: failed to open target file!\n", ptoc->name);
        return -1;
    }

    /* Open archive (source) file... */
    archive_fp = pyi_path_fopen(status->archivename, "rb");
    if (archive_fp == NULL) {
        FATALERROR("Failed to extract %s: failed to open archive file!\n", ptoc->name);
        rc = -1;
        goto cleanup;
    }
    /* ... and seek to the beginning of entry's data */
    if (pyi_fseek(archive_fp, status->pkgstart + ptoc->pos, SEEK_SET) < 0) {
        FATAL_PERROR("fseek", "Failed to extract %s: failed to seek to the entry's data!\n", ptoc->name);
        rc = -1;
        goto cleanup;
    }

    /* Extract */
    if (ptoc->cflag == '\1') {
        rc = _pyi_arch_extract_compressed(archive_fp, ptoc, out_fp, NULL);
    } else {
        rc = _pyi_arch_extract2fs_uncompressed(archive_fp, ptoc, out_fp);
    }
#ifndef WIN32
    if (ptoc->typcd == ARCHIVE_ITEM_BINARY) {
        fchmod(fileno(out_fp), S_IRUSR | S_IWUSR | S_IXUSR);
    } else {
        fchmod(fileno(out_fp), S_IRUSR | S_IWUSR);
    }
#endif

cleanup:
    /* Might be NULL if we jumped here due to fopen() failure */
    if (archive_fp) {
        fclose(archive_fp);
    }
    fclose(out_fp);

    return rc;
}


/*
 * Perform full back-to-front scan of the file to search for the
 * MAGIC pattern of the embedded archive's COOKIE header.
 *
 * Returns offset within the file if MAGIC pattern is found, 0 otherwise.
 */
static uint64_t
_pyi_find_pkg_cookie_offset(FILE *fp)
{
    /* Prepare MAGIC pattern; we need to do this programmatically to
     * prevent the pattern itself being stored in the code and matched
     * when we scan the executable */
    unsigned char magic[8];
    memcpy(magic, MAGIC_BASE, sizeof(magic));
    magic[3] += 0x0C; /* 0x00 -> 0x0C */

    /* Search using the helper */
    return pyi_utils_find_magic_pattern(fp, magic, sizeof(magic));
}

/*
 * Fix the endianness of fields in the TOC entries.
 */
static void
_pyi_arch_fix_toc_endianess(ARCHIVE_STATUS *status)
{
    TOC *ptoc = status->tocbuff;
    while (ptoc < status->tocend) {
        /* Fixup the current entry */
        ptoc->structlen = pyi_be32toh(ptoc->structlen);
        ptoc->pos = pyi_be32toh(ptoc->pos);
        ptoc->len = pyi_be32toh(ptoc->len);
        ptoc->ulen = pyi_be32toh(ptoc->ulen);
        /* Jump to next entry; with the current entry fixed up, we can
         * use non-const equivalent of pyi_arch_increment_toc_ptr() */
        ptoc = (TOC *)((const char *)ptoc + ptoc->structlen);
    }
}

/*
 * Open the archive.
 * Sets f_archiveFile, f_pkgstart, f_tocbuff and f_cookie.
 */
int
pyi_arch_open(ARCHIVE_STATUS *status)
{
    FILE *archive_fp = NULL;
    uint64_t cookie_pos = 0;
    int rc = -1;

    VS("LOADER: archivename is %s\n", status->archivename);

    /* Open the archive file */
    archive_fp = pyi_path_fopen(status->archivename, "rb");
    if (archive_fp == NULL) {
        VS("LOADER: Cannot open archive: %s\n", status->archivename);
        return -1;
    }

    /* Search for the embedded archive's cookie */
    cookie_pos = _pyi_find_pkg_cookie_offset(archive_fp);
    if (cookie_pos == 0) {
        VS("LOADER: Cannot find cookie!\n");
        goto cleanup;
    }
    VS("LOADER: Cookie found at offset 0x%" PRIX64 "\n", cookie_pos);

    /* Read the cookie */
    if (pyi_fseek(archive_fp, cookie_pos, SEEK_SET) < 0) {
        FATAL_PERROR("fseek", "Failed to seek to cookie position!\n");
        goto cleanup;
    }
    if (fread(&status->cookie, sizeof(COOKIE), 1, archive_fp) < 1) {
        FATAL_PERROR("fread", "Failed to read cookie!\n");
        goto cleanup;
    }
    /* Fix endianness of COOKIE fields */
    status->cookie.len = pyi_be32toh(status->cookie.len);
    status->cookie.TOC = pyi_be32toh(status->cookie.TOC);
    status->cookie.TOClen = pyi_be32toh(status->cookie.TOClen);
    status->cookie.pyvers = pyi_be32toh(status->cookie.pyvers);

    /* From the cookie position and declared archive size, calculate
     * the archive start position */
    status->pkgstart = cookie_pos + sizeof(COOKIE) - status->cookie.len;

    /* Set the flag that Python library was not loaded yet. */
    status->is_pylib_loaded = false;

    /* Set the the Python version used. */
    pyvers = pyi_arch_get_pyversion(status);

    /* Read in in the table of contents */
    pyi_fseek(archive_fp, status->pkgstart + status->cookie.TOC, SEEK_SET);
    status->tocbuff = (TOC *)malloc(status->cookie.TOClen);

    if (status->tocbuff == NULL) {
        FATAL_PERROR("malloc", "Could not allocate buffer for TOC!\n");
        goto cleanup;
    }

    if (fread(status->tocbuff, status->cookie.TOClen, 1, archive_fp) < 1) {
        FATAL_PERROR("fread", "Could not read full TOC!\n");
        goto cleanup;
    }
    status->tocend = (const TOC *)(((const char *)status->tocbuff) + status->cookie.TOClen);

    /* Check input file is still ok (should be). */
    if (ferror(archive_fp)) {
        FATALERROR("Error on file.\n");
        goto cleanup;
    }

    /* Fix the endianness of the fields in the TOC entries */
    _pyi_arch_fix_toc_endianess(status);

    rc = 0; /* Succeeded */

cleanup:
    fclose(archive_fp);

    return rc;
}

/* Check if the TOC entry corresponds to extractable file */
static bool
_pyi_arch_is_extractable(const TOC *ptoc)
{
    switch (ptoc->typcd) {
        /* onefile mode */
        case ARCHIVE_ITEM_BINARY:
        case ARCHIVE_ITEM_DATA:
        case ARCHIVE_ITEM_ZIPFILE:
        case ARCHIVE_ITEM_SYMLINK: {
            return true;
        }
        /* MERGE mode */
        case ARCHIVE_ITEM_DEPENDENCY: {
            return true;
        }
        default: {
            break;
        }
    }

    return false;
}

/* Setup the archive with python modules and the paths required by rest of
 * this module (this always needs to be done).
 * Sets f_archivename, f_homepath, f_mainpath
 */
bool
pyi_arch_setup(ARCHIVE_STATUS *status, char const *archive_path, char const *executable_path)
{
    const TOC *ptoc;

    /* Copy archive path and executable path */
    if (snprintf(status->archivename, PATH_MAX, "%s", archive_path) >= PATH_MAX) {
        return false;
    }
    if (snprintf(status->executablename, PATH_MAX, "%s", executable_path) >= PATH_MAX) {
        return false;
    }

    /* Try to open the archive with given archive and executable path */
    if (pyi_arch_open(status)) {
        return false;
    }

    /* Check if contents need to be extracted */
    status->needs_to_extract = false;

    ptoc = status->tocbuff;
    while (ptoc < status->tocend) {
        if (_pyi_arch_is_extractable(ptoc)) {
            status->needs_to_extract = true;
            break;
        }
        ptoc = pyi_arch_increment_toc_ptr(status, ptoc);
    }

    /* Set homepath (a.k.a. sys._MEIPASS) */
    char executable_dir[PATH_MAX];
    pyi_path_dirname(executable_dir, executable_path);
#if defined(__APPLE__)
    size_t executable_dir_len;
    executable_dir_len = strnlen(executable_dir, PATH_MAX);
    bool is_macos_app_bundle = executable_dir_len > 19 && strncmp(executable_dir + executable_dir_len - 19, ".app/Contents/MacOS", 19) == 0;
#else
    bool is_macos_app_bundle = false;
#endif
    if (is_macos_app_bundle) {
        /* macOS .app bundle; relocate homepath from Contents/MacOS
         * directory to Contents/Frameworks */
        char contents_dir[PATH_MAX];
        pyi_path_dirname(contents_dir, executable_dir);
        pyi_path_join(status->homepath, contents_dir, "Frameworks");
    } else {
        const char *contents_directory = pyi_arch_get_option(status, "pyi-contents-directory");
        if (contents_directory && status->needs_to_extract == false) {
            char root_path[PATH_MAX];
            pyi_path_dirname(root_path, archive_path);
            pyi_path_join(status->homepath, root_path, contents_directory);
        } else {
            pyi_path_dirname(status->homepath, archive_path);
        }
    }

    /*
     * Initial value of mainpath is homepath. It might be overridden
     * by temppath if it is available.
     */
    status->has_temp_directory = false;
    strcpy(status->mainpath, status->homepath);

    return true;
}

/*
 * Helpers for embedders.
 */
int
pyi_arch_get_pyversion(const ARCHIVE_STATUS *status)
{
    return status->cookie.pyvers;
}

/*
 * Allocate memory for archive status.
 */
ARCHIVE_STATUS *
pyi_arch_status_new()
{
    ARCHIVE_STATUS *archive_status;
    archive_status = (ARCHIVE_STATUS *)calloc(1, sizeof(ARCHIVE_STATUS));
    if (archive_status == NULL) {
        FATAL_PERROR("calloc", "Cannot allocate memory for ARCHIVE_STATUS\n");
    }
    return archive_status;
}

/*
 * Free memory allocated for archive status.
 */
void
pyi_arch_status_free(ARCHIVE_STATUS *archive_status)
{
    if (archive_status == NULL) {
        return;
    }

    VS("LOADER: Freeing archive status for %s\n", archive_status->archivename);

    /* Free the TOC buffer */
    free(archive_status->tocbuff);

    /* Free the structure itself */
    free(archive_status);
}

/*
 * Returns the value of the pyi bootloader option given by optname. Returns
 * NULL if the option is not present. Returns an empty string if the option is present,
 * but has no associated value.
 *
 * The string returned is owned by the ARCHIVE_STATUS; the caller is NOT responsible
 * for freeing it.
 */
const char *
pyi_arch_get_option(const ARCHIVE_STATUS *status, const char *optname)
{
    /* TODO: option-cache? */
    size_t optlen;
    const TOC *ptoc = status->tocbuff;

    optlen = strlen(optname);

    for (; ptoc < status->tocend; ptoc = pyi_arch_increment_toc_ptr(status, ptoc)) {
        if (ptoc->typcd == ARCHIVE_ITEM_RUNTIME_OPTION) {
            if (0 == strncmp(ptoc->name, optname, optlen)) {
                if (0 != ptoc->name[optlen]) {
                    /* Space separates option name from option value, so add 1. */
                    return ptoc->name + optlen + 1;
                }
                else {
                    /* No option value, just return the empty string. */
                    return ptoc->name + optlen;
                }
            }
        }
    }
    return NULL;
}

/*
 * Find a TOC entry by its name and return it.
 */
const TOC *
pyi_arch_find_by_name(const ARCHIVE_STATUS *status, const char *name)
{
    const TOC *ptoc = status->tocbuff;

    while (ptoc < status->tocend) {
#if defined(_WIN32) || defined(__APPLE__)
        /* On Windows and macOS, use case-insensitive comparison to
         * simulate case-insensitive filesystem for extractable entries. */
        if (_pyi_arch_is_extractable(ptoc)) {
            if (strcasecmp(ptoc->name, name) == 0) {
                return ptoc;
            }
        } else {
            if (strcmp(ptoc->name, name) == 0) {
                return ptoc;
            }
        }
#else
        if (strcmp(ptoc->name, name) == 0) {
            return ptoc;
        }
#endif
        ptoc = pyi_arch_increment_toc_ptr(status, ptoc);
    }
    return NULL;
}


/*
 * Creates a temporary directory for the ARCHIVE_STATUS.
 */
int
pyi_arch_create_tempdir(ARCHIVE_STATUS *status)
{
    const char *runtime_tmpdir = NULL;

    /* No-op if already initialized */
    if (status->has_temp_directory == true) {
        return 0;
    }

    /* Check for custom run-time temporary directory options */
    runtime_tmpdir = pyi_arch_get_option(status, "pyi-runtime-tmpdir");
    if (runtime_tmpdir != NULL) {
        VS("LOADER: Found runtime-tmpdir %s\n", runtime_tmpdir);
    }

    if (!pyi_create_tempdir(status->temppath, runtime_tmpdir)) {
        FATALERROR("Cannot create temporary directory!\n");
        return -1;
    }

    /* Set flag that temp directory is created and available. */
    status->has_temp_directory = true;

    return 0;
}
