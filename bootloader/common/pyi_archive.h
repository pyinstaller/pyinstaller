/*
 * Declarations related to an PyInstaller archive.
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
#ifndef HEADER_PYI_ARCHIVE_H
#define HEADER_PYI_ARCHIVE_H

#include <stdio.h>

#include "pyi_global.h"


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

/* TOC entry for a CArchive */
typedef struct _toc {
    int structlen;    /*len of this one - including full len of name */
    int pos;          /* pos rel to start of concatenation */
    int len;          /* len of the data (compressed) */
    int ulen;         /* len of data (uncompressed) */
    char cflag;       /* is it compressed (really a byte) */
    char typcd;       /* type code -'b' binary, 'z' zlib, 'm' module,
                       * 's' script (v3),'x' data, 'o' runtime option  */
    char name[1];    /* the name to save it as */
	/* starting in v5, we stretch this out to a mult of 16 */
} TOC;

/* The CArchive Cookie, from end of the archive. */
typedef struct _cookie {
    char magic[8]; /* 'MEI\014\013\012\013\016' */
    int  len;      /* len of entire package */
    int  TOC;      /* pos (rel to start) of TableOfContents */
    int  TOClen;   /* length of TableOfContents */
    int  pyvers;   /* new in v4 */
    char pylibname[64];    /* Filename of Python dynamic library e.g. python2.7.dll. */
} COOKIE;

typedef struct _archive_status {
    FILE    *fp;
    int     pkgstart;
    TOC     *tocbuff;
    TOC     *tocend;
    COOKIE  cookie;
    char    archivename[PATH_MAX + 1];
    char    homepath[PATH_MAX + 1];
    char    temppath[PATH_MAX + 1];
#ifdef WIN32
    char    homepathraw[PATH_MAX + 1];
    char    temppathraw[PATH_MAX + 1];
#endif
    /* 
     * Flag if running in onefile mode. Bootloader has to behave differently
     * in this mode.
     */
    bool_t  is_onefile_mode;
} ARCHIVE_STATUS;


#endif /* HEADER_PYI_ARCHIVE_H */
