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


/*
 * Return pointer to the next TOC entry in the TOC buffer.
 */
const struct TOC_ENTRY *
pyi_archive_next_toc_entry(const struct ARCHIVE *archive, const struct TOC_ENTRY *toc_entry)
{
    return (const struct TOC_ENTRY *)((const char *)toc_entry + toc_entry->entry_length);
}


/*
 * Helper for pyi_archive_extract/pyi_archive_extract2fs that extracts a
 * compressed file from the archive, and writes it into the provided
 * file handle or data buffer. Exactly one of out_fp or out_ptr needs
 * to be valid.
 */
static int
_pyi_archive_extract_compressed(FILE *archive_fp, const struct TOC_ENTRY *toc_entry, FILE *out_fp, unsigned char *out_ptr)
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
        PYI_ERROR("Failed to extract %s: inflateInit() failed with return code %d!\n", toc_entry->name, rc);
        return -1;
    }

    /* Allocate I/O buffers */
    buffer_in = (unsigned char *)malloc(CHUNK_SIZE);
    if (buffer_in == NULL) {
        PYI_PERROR("malloc", "Failed to extract %s: failed to allocate temporary input buffer!\n", toc_entry->name);
        goto cleanup;
    }
    buffer_out = (unsigned char *)malloc(CHUNK_SIZE);
    if (buffer_out == NULL) {
        PYI_PERROR("malloc", "Failed to extract %s: failed to allocate temporary output buffer!\n", toc_entry->name);
        goto cleanup;
    }

    /* Decompress until deflate stream ends or end of file is reached */
    remaining_size = toc_entry->length;
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
        PYI_ERROR("Failed to extract %s: decompression resulted in return code %d!\n", toc_entry->name, rc);
        rc = -1;
    }

cleanup:
    inflateEnd(&zstream);
    free(buffer_in);
    free(buffer_out);

    return rc;
}

/*
 * Helper for pyi_archive_extract2fs that extracts an uncompressed file
 * from the archive into the provided file handle.
 */
static int
_pyi_archive_extract2fs_uncompressed(FILE *archive_fp, const struct TOC_ENTRY *toc_entry, FILE *out_fp)
{
    const size_t CHUNK_SIZE = 8192;
    unsigned char *buffer;
    uint64_t remaining_size;
    int rc = 0;

    /* Allocate temporary buffer for a single chunk */
    buffer = (unsigned char *)malloc(CHUNK_SIZE);
    if (buffer == NULL) {
        PYI_PERROR("malloc", "Failed to extract %s: failed to allocate temporary buffer!\n", toc_entry->name);
        return -1;
    }

    /* ... and copy it, chunk by chunk */
    remaining_size = toc_entry->uncompressed_length;
    while (remaining_size > 0) {
        size_t chunk_size = (CHUNK_SIZE < remaining_size) ? CHUNK_SIZE : (size_t)remaining_size;
        if (fread(buffer, chunk_size, 1, archive_fp) < 1) {
            PYI_PERROR("fread", "Failed to extract %s: failed to read data chunk!\n", toc_entry->name);
            rc = -1;
            break;
        }
        if (fwrite(buffer, chunk_size, 1, out_fp) < 1) {
            PYI_PERROR("fwrite", "Failed to extract %s: failed to write data chunk!\n", toc_entry->name);
            rc = -1;
            break;
        }
        remaining_size -= chunk_size;
    }
    free(buffer);
    return rc;
}

/*
 * Helper for pyi_archive_extract that extracts an uncompressed file from
 * the archive into the provided (pre-allocated) buffer.
 */
static int
_pyi_archive_extract_uncompressed(FILE *archive_fp, const struct TOC_ENTRY *toc_entry, unsigned char *out_buf)
{
    const size_t CHUNK_SIZE = 8192;
    unsigned char *buffer;
    uint64_t remaining_size;

    /* Read the file into buffer, chunk by chunk */
    buffer = out_buf;
    remaining_size = toc_entry->uncompressed_length;
    while (remaining_size > 0) {
        size_t chunk_size = (CHUNK_SIZE < remaining_size) ? CHUNK_SIZE : (size_t)remaining_size;
        if (fread(buffer, chunk_size, 1, archive_fp) < 1) {
            PYI_PERROR("fread", "Failed to extract %s: failed to read data chunk!\n", toc_entry->name);
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
pyi_archive_extract(const struct ARCHIVE *archive, const struct TOC_ENTRY *toc_entry)
{
    FILE *archive_fp = NULL;
    unsigned char *data = NULL;
    int rc = 0;

    /* Open archive (source) file... */
    archive_fp = pyi_path_fopen(archive->filename, "rb");
    if (archive_fp == NULL) {
        PYI_ERROR("Failed to extract %s: failed to open archive file!\n", toc_entry->name);
        return NULL;
    }
    /* ... and seek to the beginning of entry's data */
    if (pyi_fseek(archive_fp, archive->pkg_offset + toc_entry->offset, SEEK_SET) < 0) {
        PYI_PERROR("fseek", "Failed to extract %s: failed to seek to the entry's data!\n", toc_entry->name);
        goto cleanup;
    }

    /* Allocate the data buffer */
    data = (unsigned char *)malloc(toc_entry->uncompressed_length);
    if (data == NULL) {
        PYI_PERROR("malloc", "Failed to extract %s: failed to allocate data buffer (%u bytes)!\n", toc_entry->name, toc_entry->uncompressed_length);
        goto cleanup;
    }

    /* Extract */
    if (toc_entry->compression_flag == 1) {
        rc = _pyi_archive_extract_compressed(archive_fp, toc_entry, NULL, data);
    } else {
        rc = _pyi_archive_extract_uncompressed(archive_fp, toc_entry, data);
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
_pyi_archive_create_symlink(const struct ARCHIVE *archive, const struct TOC_ENTRY *toc_entry, const char *output_filename)
{
    char *link_target = NULL;
    int rc = -1;

    /* Extract symlink target */
    link_target = (char *)pyi_archive_extract(archive, toc_entry);
    if (!link_target) {
        goto cleanup;
    }

    /* Create the symbolic link */
    rc = pyi_path_mksymlink(link_target, output_filename);

cleanup:
    free(link_target);

    return rc;
}

/*
 * Extract an archive entry into specified output file.
 */
int
pyi_archive_extract2fs(const struct ARCHIVE *archive, const struct TOC_ENTRY *toc_entry, const char *output_filename)
{
    FILE *archive_fp = NULL;
    FILE *out_fp = NULL;
    int rc = 0;

    /* Handle symbolic links */
    if (toc_entry->typecode == ARCHIVE_ITEM_SYMLINK) {
        rc = _pyi_archive_create_symlink(archive, toc_entry, output_filename);
        if (rc < 0) {
            PYI_ERROR("Failed to create symbolic link %s!\n", toc_entry->name);
        }
        return rc;
    }

    /* Open target file */
    out_fp = pyi_path_fopen(output_filename, "wb");
    if (out_fp == NULL) {
        PYI_PERROR("fopen", "Failed to extract %s: failed to open target file!\n", toc_entry->name);
        return -1;
    }

    /* Open archive (source) file... */
    archive_fp = pyi_path_fopen(archive->filename, "rb");
    if (archive_fp == NULL) {
        PYI_ERROR("Failed to extract %s: failed to open archive file!\n", toc_entry->name);
        rc = -1;
        goto cleanup;
    }
    /* ... and seek to the beginning of entry's data */
    if (pyi_fseek(archive_fp, archive->pkg_offset + toc_entry->offset, SEEK_SET) < 0) {
        PYI_PERROR("fseek", "Failed to extract %s: failed to seek to the entry's data!\n", toc_entry->name);
        rc = -1;
        goto cleanup;
    }

    /* Extract */
    if (toc_entry->compression_flag == 1) {
        rc = _pyi_archive_extract_compressed(archive_fp, toc_entry, out_fp, NULL);
    } else {
        rc = _pyi_archive_extract2fs_uncompressed(archive_fp, toc_entry, out_fp);
    }
#ifndef WIN32
    if (toc_entry->typecode == ARCHIVE_ITEM_BINARY) {
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
_pyi_archive_find_pkg_cookie_offset(FILE *fp)
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

/* Check if the TOC entry's typecode corresponds to an extractable file */
static bool
_pyi_archive_is_extractable(char typecode)
{
    switch (typecode) {
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

/*
 * Open the archive.
 */
struct ARCHIVE *
pyi_archive_open(const char *filename)
{
    FILE *archive_fp = NULL;
    uint64_t cookie_pos = 0;
    struct ARCHIVE_COOKIE archive_cookie;
    struct ARCHIVE *archive = NULL;
    struct TOC_ENTRY *toc_entry;

    PYI_DEBUG("LOADER: attempting to open archive %s\n", filename);

    /* Open the archive file */
    archive_fp = pyi_path_fopen(filename, "rb");
    if (archive_fp == NULL) {
        PYI_DEBUG("LOADER: cannot open archive: %s\n", filename);
        return NULL;
    }

    /* Search for the embedded archive's cookie */
    cookie_pos = _pyi_archive_find_pkg_cookie_offset(archive_fp);
    if (cookie_pos == 0) {
        PYI_DEBUG("LOADER: cannot find cookie!\n");
        goto cleanup;
    }
    PYI_DEBUG("LOADER: cookie found at offset 0x%" PRIX64 "\n", cookie_pos);

    /* Read the cookie */
    if (pyi_fseek(archive_fp, cookie_pos, SEEK_SET) < 0) {
        PYI_PERROR("fseek", "Failed to seek to cookie position!\n");
        goto cleanup;
    }
    if (fread(&archive_cookie, sizeof(struct ARCHIVE_COOKIE), 1, archive_fp) < 1) {
        PYI_PERROR("fread", "Failed to read cookie!\n");
        goto cleanup;
    }

    /* Allocate the structure */
    archive = (struct ARCHIVE *)calloc(1, sizeof(struct ARCHIVE));
    if (archive == NULL) {
        PYI_PERROR("calloc", "Could not allocate memory for archive structure!\n");
        goto cleanup;
    }

    /* Copy the filename; since the input buffer originates from within
     * bootloader, the string is guaranteed to be within PYI_PATH_MAX limit */
    snprintf(archive->filename, PYI_PATH_MAX, "%s", filename);

    /* Fix endianness of cookie fields */
    archive_cookie.pkg_length = pyi_be32toh(archive_cookie.pkg_length);
    archive_cookie.toc_offset = pyi_be32toh(archive_cookie.toc_offset);
    archive_cookie.toc_length = pyi_be32toh(archive_cookie.toc_length);
    archive_cookie.python_version = pyi_be32toh(archive_cookie.python_version);

    /* Copy python version and python shared library name from cookie */
    archive->python_version = archive_cookie.python_version;
    snprintf(archive->python_libname, 64, "%s", archive_cookie.python_libname);

    /* From the cookie position and declared archive size, calculate
     * the archive start position */
    archive->pkg_offset = cookie_pos + sizeof(struct ARCHIVE_COOKIE) - archive_cookie.pkg_length;

    /* Read the table of contents (TOC) */
    pyi_fseek(archive_fp, archive->pkg_offset + archive_cookie.toc_offset, SEEK_SET);
    archive->toc = (struct TOC_ENTRY *)malloc(archive_cookie.toc_length);

    if (archive->toc == NULL) {
        PYI_PERROR("malloc", "Could not allocate buffer for TOC!\n");
        goto cleanup;
    }

    if (fread(archive->toc, archive_cookie.toc_length, 1, archive_fp) < 1) {
        PYI_PERROR("fread", "Could not read full TOC!\n");
        goto cleanup;
    }
    archive->toc_end = (const struct TOC_ENTRY *)(((const char *)archive->toc) + archive_cookie.toc_length);

    /* Check input file is still ok (should be). */
    if (ferror(archive_fp)) {
        PYI_ERROR("Error on file.\n");
        goto cleanup;
    }

    /* Fix the endianness of the fields in the TOC entries. At the same
     * time, check for extractable entries that imply onefile semantics. */
    toc_entry = archive->toc;
    while (toc_entry < archive->toc_end) {
        /* Fixup the current TOC entry */
        toc_entry->entry_length = pyi_be32toh(toc_entry->entry_length);
        toc_entry->offset = pyi_be32toh(toc_entry->offset);
        toc_entry->length = pyi_be32toh(toc_entry->length);
        toc_entry->uncompressed_length = pyi_be32toh(toc_entry->uncompressed_length);

        /* Check if entry is extractable */
        archive->contains_extractable_entries |= _pyi_archive_is_extractable(toc_entry->typecode);

        /* Check if this is SPLASH entry */
        if (toc_entry->typecode == ARCHIVE_ITEM_SPLASH) {
            archive->toc_splash = toc_entry;
        }

        /* Jump to next entry; with the current entry fixed up, we can
         * use non-const equivalent of pyi_archive_next_toc_entry() */
        toc_entry = (struct TOC_ENTRY *)((const char *)toc_entry + toc_entry->entry_length);
    }

cleanup:
    fclose(archive_fp);

    return archive;
}


/*
 * Free memory allocated for archive status. The archive structure is
 * passed via pointer to location that stores the structure - this
 * location is also cleared to NULL.
 */
void
pyi_archive_free(struct ARCHIVE **archive_ref)
{
    struct ARCHIVE *archive = *archive_ref;

    *archive_ref = NULL;

    if (archive == NULL) {
        return;
    }

    /* Free the TOC buffer */
    free(archive->toc);

    /* Free the structure itself */
    free(archive);
}


/*
 * Find a TOC entry by its name and return it.
 */
const struct TOC_ENTRY *
pyi_archive_find_entry_by_name(const struct ARCHIVE *archive, const char *name)
{
    const struct TOC_ENTRY *toc_entry;

    for (toc_entry = archive->toc; toc_entry < archive->toc_end; toc_entry = pyi_archive_next_toc_entry(archive, toc_entry)) {
#if defined(_WIN32) || defined(__APPLE__)
        /* On Windows and macOS, use case-insensitive comparison to
         * simulate case-insensitive filesystem for extractable entries. */
        if (_pyi_archive_is_extractable(toc_entry->typecode)) {
            if (strcasecmp(toc_entry->name, name) == 0) {
                return toc_entry;
            }
        } else {
            if (strcmp(toc_entry->name, name) == 0) {
                return toc_entry;
            }
        }
#else
        if (strcmp(toc_entry->name, name) == 0) {
            return toc_entry;
        }
#endif
    }

    return NULL;
}
