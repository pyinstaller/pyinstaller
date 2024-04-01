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

/* TOC entry for a CArchive */
typedef struct _toc {
    int  structlen;  /*len of this one - including full len of name */
    uint32_t pos;    /* pos rel to start of concatenation */
    uint32_t len;    /* len of the data (compressed) */
    uint32_t ulen;   /* len of data (uncompressed) */
    char cflag;      /* is it compressed (really a byte) */
    char typcd;      /* type code -'b' binary, 'z' zlib, 'm' module,
                      * 's' script (v3),'x' data, 'o' runtime option  */
    char name[1];    /* the name to save it as */
    /* starting in v5, we stretch this out to a mult of 16 */
} TOC;

/* The CArchive Cookie, from end of the archive. */
typedef struct _cookie {
    char magic[8];      /* 'MEI\014\013\012\013\016' */
    uint32_t len;       /* len of entire package */
    uint32_t TOC;       /* pos (rel to start) of TableOfContents */
    int  TOClen;        /* length of TableOfContents */
    int  pyvers;        /* new in v4 */
    char pylibname[64]; /* Filename of Python dynamic library e.g. python2.7.dll. */
} COOKIE;

typedef struct _archive_status
{
    /* Full path to archive file. */
    char filename[PATH_MAX];

    uint64_t pkgstart;
    TOC *tocbuff;
    const TOC *tocend;
    COOKIE cookie;

    /* Flag indicating that the archive contains extractable files,
     * and thus has onefile semantics */
    bool contains_extractable_entries;
} ARCHIVE_STATUS;


/* Structure allocation and cleanup */
ARCHIVE_STATUS *pyi_arch_status_new();
void pyi_arch_status_free(ARCHIVE_STATUS *status);

/* Open the archive */
int pyi_arch_open(ARCHIVE_STATUS *archive, const char *filename);

const TOC *pyi_arch_increment_toc_ptr(const ARCHIVE_STATUS *status, const TOC *ptoc);

unsigned char *pyi_arch_extract(const ARCHIVE_STATUS *status, const TOC *ptoc);
int pyi_arch_extract2fs(const ARCHIVE_STATUS *archive, const TOC *toc_entry, const char *output_directory);

/**
 * Helpers for embedders
 */
int pyi_arch_get_pyversion(const ARCHIVE_STATUS *status);
extern int pyvers;

const char *pyi_arch_get_option(const ARCHIVE_STATUS *status, const char *optname);
const TOC *pyi_arch_find_by_name(const ARCHIVE_STATUS *status, const char *name);

#endif  /* PYI_ARCHIVE_H */
