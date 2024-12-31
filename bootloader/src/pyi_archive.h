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
 * Declarations related to an PyInstaller archive.
 */

#ifndef PYI_ARCHIVE_H
#define PYI_ARCHIVE_H

#include "pyi_global.h"
#include <stdio.h>  /* FILE */
#include <inttypes.h>  /* uint64_t */

/* Types of CArchive items. */
#define ARCHIVE_ITEM_BINARY           'b'  /* binary */
#define ARCHIVE_ITEM_DEPENDENCY       'd'  /* runtime option */
#define ARCHIVE_ITEM_PYZ              'z'  /* zlib (pyz) - frozen Python code */
#define ARCHIVE_ITEM_ZIPFILE          'Z'  /* zlib (pyz) - frozen Python code */
#define ARCHIVE_ITEM_PYPACKAGE        'M'  /* Python package (__init__.py) */
#define ARCHIVE_ITEM_PYMODULE         'm'  /* Python module */
#define ARCHIVE_ITEM_PYSOURCE         's'  /* Python script (v3) */
#define ARCHIVE_ITEM_DATA             'x'  /* data */
#define ARCHIVE_ITEM_RUNTIME_OPTION   'o'  /* runtime option */
#define ARCHIVE_ITEM_SPLASH           'l'  /* splash resources */
#define ARCHIVE_ITEM_SYMLINK          'n'  /* symbolic link */

/* Entry in PKG/CArchive TOC */
struct TOC_ENTRY
{
    uint32_t entry_length; /* length of this TOC entry, including full length of the name field */
    uint32_t offset; /* position of entry's data blob, relative to the start of PKG archive */
    uint32_t length; /* length of compressed data blob */
    uint32_t uncompressed_length; /* length of uncompressed data blob */
    unsigned char compression_flag; /* compression flag (1 = compressed, 0 = uncompressed) */
    char typecode; /* type code - see ARCHIVE_ITEM_* definitions */
    char name[1];  /* entry name; padded to multiple of 16 */
};

/* The PKG/CArchive cookie, from the end of the archive. */
struct ARCHIVE_COOKIE
{
    char magic[8]; /* 'MEI\014\013\012\013\016' */
    uint32_t pkg_length; /* length of the entire PKG archive */
    uint32_t toc_offset; /* position of TOC relative to start of PKG archive */
    uint32_t toc_length; /* length of TOC data */
    uint32_t python_version; /* integer representing python version */
    char python_libname[64]; /* Name of the of Python shared library (e.g., "python3.10.dll"). */
};

/* The archive structure */
struct ARCHIVE
{
    /* Full path to archive file. */
    char filename[PYI_PATH_MAX];

    uint64_t pkg_offset; /* Offset of the PKG archive in the file */

    struct TOC_ENTRY *toc; /* Buffer containing all TOC entries */
    const struct TOC_ENTRY *toc_end; /* The address at which the TOC buffer ends */

    /* Flag indicating that the archive contains extractable files,
     * and thus has onefile semantics */
    bool contains_extractable_entries;

    /* Pointer to SPLASH TOC entry, if available */
    const struct TOC_ENTRY *toc_splash;

    /* Python version: major * 100 + minor, e.g., 310 for python 3.10 */
    int python_version;

    /* The name of python shared library */
    char python_libname[64];
};


/* The API */
struct ARCHIVE *pyi_archive_open(const char *filename);
void pyi_archive_free(struct ARCHIVE **archive_ref);

const struct TOC_ENTRY *pyi_archive_next_toc_entry(const struct ARCHIVE *archive, const struct TOC_ENTRY *toc_entry);

unsigned char *pyi_archive_extract(const struct ARCHIVE *archive, const struct TOC_ENTRY *toc_entry);
int pyi_archive_extract2fs(const struct ARCHIVE *archive, const struct TOC_ENTRY *toc_entry, const char *output_filename);

const struct TOC_ENTRY *pyi_archive_find_entry_by_name(const struct ARCHIVE *archive, const char *name);

#endif /* PYI_ARCHIVE_H */
