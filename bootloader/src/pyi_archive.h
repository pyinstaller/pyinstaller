/*
 * ****************************************************************************
 * Copyright (c) 2013-2018, PyInstaller Development Team.
 * Distributed under the terms of the GNU General Public License with exception
 * for distributing bootloader.
 *
 * The full license is in the file COPYING.txt, distributed with this software.
 * ****************************************************************************
 */

/*
 * Declarations related to an PyInstaller archive.
 */

#ifndef PYI_ARCHIVE_H
#define PYI_ARCHIVE_H

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
    int  structlen;  /*len of this one - including full len of name */
    int  pos;        /* pos rel to start of concatenation */
    int  len;        /* len of the data (compressed) */
    int  ulen;       /* len of data (uncompressed) */
    char cflag;      /* is it compressed (really a byte) */
    char typcd;      /* type code -'b' binary, 'z' zlib, 'm' module,
                      * 's' script (v3),'x' data, 'o' runtime option  */
    char name[1];    /* the name to save it as */
    /* starting in v5, we stretch this out to a mult of 16 */
} TOC;

/* The CArchive Cookie, from end of the archive. */
typedef struct _cookie {
    char magic[8];      /* 'MEI\014\013\012\013\016' */
    int  len;           /* len of entire package */
    int  TOC;           /* pos (rel to start) of TableOfContents */
    int  TOClen;        /* length of TableOfContents */
    int  pyvers;        /* new in v4 */
    char pylibname[64]; /* Filename of Python dynamic library e.g. python2.7.dll. */
} COOKIE;

typedef struct _archive_status {
    FILE * fp;
    int    pkgstart;
    TOC *  tocbuff;
    TOC *  tocend;
    COOKIE cookie;
    /*
     * On Windows:
     *    These strings are UTF-8 encoded (via pyi_win32_utils_to_utf8). On Python 2,
     *    they are re-encoded to ANSI with ShortFileNames when passed to Python. On
     *    Python 3, they are decoded back to wchar_t.
     *
     * On Linux/OS X:
     *    These strings are system-provided. On Python 2, they are passed as-is to Python.
     *    On Python 3, they are decoded to wchar_t using Py_DecodeLocale
     *    (formerly called _Py_char2wchar) first.
     */
    char archivename[PATH_MAX];
    char homepath[PATH_MAX];
    char temppath[PATH_MAX];
    /*
     * Main path could be homepath or temppath. It will be temppath
     * if temppath is available. Sometimes we do not need to know if temppath
     * or homepath should be used. We only need to know the path. This variable
     * is used for example to set sys.path, sys.prefix, and sys._MEIPASS.
     */
    char mainpath[PATH_MAX];
    /*
     * Flag if temporary directory is available. This usually means running
     * executable in onefile mode. Bootloader has to behave differently
     * in this mode.
     */
    bool has_temp_directory;
    /*
     * Flag if Python library was loaded. This indicates if it is safe
     * to call function PI_Py_Finalize(). If Python dll is missing
     * calling this function would cause segmentation fault.
     */
    bool is_pylib_loaded;
    /*
     * Cached command-line arguments.
     */
    int    argc;      /* Count of command-line arguments. */
    char **argv;      /*
                       * On Windows, UTF-8 encoded form of __wargv.
                       * On OS X/Linux, as received in main()
                       */
} ARCHIVE_STATUS;

TOC *pyi_arch_increment_toc_ptr(const ARCHIVE_STATUS *status, const TOC* ptoc);

unsigned char *pyi_arch_extract(ARCHIVE_STATUS *status, TOC *ptoc);
int pyi_arch_extract2fs(ARCHIVE_STATUS *status, TOC *ptoc);

/**
 * Helpers for embedders
 */
int pyi_arch_get_pyversion(ARCHIVE_STATUS *status);
extern int pyvers;

/**
 * The gory detail level
 */
int pyi_arch_set_paths(ARCHIVE_STATUS *status, char const * archivePath,
                       char const * archiveName);
int pyi_arch_open(ARCHIVE_STATUS *status);

/*
 * Memory allocation wrappers.
 */
void pyi_arch_status_free_memory(ARCHIVE_STATUS *status);

/*
 * Setup the paths and open the archive
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
int pyi_arch_setup(ARCHIVE_STATUS *status, char const * archivePath,
                   char const * archiveName);

TOC *getFirstTocEntry(ARCHIVE_STATUS *status);
TOC *getNextTocEntry(ARCHIVE_STATUS *status, TOC *entry);

char * pyi_arch_get_option(const ARCHIVE_STATUS * status, char * optname);

#endif  /* PYI_ARCHIVE_H */
