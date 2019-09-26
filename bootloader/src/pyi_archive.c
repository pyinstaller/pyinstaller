/*
 * ****************************************************************************
 * Copyright (c) 2013-2019, PyInstaller Development Team.
 * Distributed under the terms of the GNU General Public License with exception
 * for distributing bootloader.
 *
 * The full license is in the file COPYING.txt, distributed with this software.
 * ****************************************************************************
 */

/*
 * Fuctions related to PyInstaller archive embedded in executable.
 */

/* TODO: use safe string functions */
#define _CRT_SECURE_NO_WARNINGS 1

#ifdef _WIN32
/* TODO verify windows includes */
    #include <winsock.h>  /* ntohl */
#else
    #include <limits.h>  /* PATH_MAX - not available on windows. */
    #ifdef __FreeBSD__
/* freebsd issue #188316 */
        #include <arpa/inet.h>  /* ntohl */
    #else
        #include <netinet/in.h>  /* ntohl */
    #endif
    #include <stdlib.h>   /* malloc */
    #include <string.h>   /* strncmp, strcpy, strcat */
    #include <sys/stat.h> /* fchmod */
#endif /* ifdef _WIN32 */
#include <stddef.h>  /* ptrdiff_t */
#include <stdio.h>

/* PyInstaller headers. */
#include "zlib.h"
#include "pyi_global.h"
#include "pyi_path.h"
#include "pyi_archive.h"
#include "pyi_utils.h"
#include "pyi_python.h"

int pyvers = 0;

/* Magic number to verify archive data are bundled correctly. */
#define MAGIC "MEI\014\013\012\013\016"

/*
 * Return pointer to next toc entry.
 */
TOC *
pyi_arch_increment_toc_ptr(const ARCHIVE_STATUS *status, const TOC* ptoc)
{
    TOC *result = (TOC*)((char *)ptoc + ntohl(ptoc->structlen));

    if (result < status->tocbuff) {
        FATALERROR("Cannot read Table of Contents.\n");
        return status->tocend;
    }
    return result;
}

/*
 * Open archive file if needed
 */
static int
pyi_arch_open_fp(ARCHIVE_STATUS *status)
{
    if (status->fp == NULL) {
        status->fp = pyi_path_fopen(status->archivename, "rb");

        if (status->fp == NULL) {
            return -1;
        }
    }
    return 0;
}

/*
 * Close archive file
 * File should close after unused to avoid locking
 */
static void
pyi_arch_close_fp(ARCHIVE_STATUS *status)
{
    if (status->fp != NULL) {
        pyi_path_fclose(status->fp);
        status->fp = NULL;
    }
}

/*
 * Decompress data in buff, described by ptoc.
 * Return in malloc'ed buffer (needs to be freed)
 */
static unsigned char *
decompress(unsigned char * buff, TOC *ptoc)
{
    const char *ver;
    unsigned char *out;
    z_stream zstream;
    int rc;

    ver = (zlibVersion)();
    out = (unsigned char *)malloc(ntohl(ptoc->ulen));

    if (out == NULL) {
        OTHERERROR("Error allocating decompression buffer\n");
        return NULL;
    }

    zstream.zalloc = NULL;
    zstream.zfree = NULL;
    zstream.opaque = NULL;
    zstream.next_in = buff;
    zstream.avail_in = ntohl(ptoc->len);
    zstream.next_out = out;
    zstream.avail_out = ntohl(ptoc->ulen);
    rc = inflateInit(&zstream);

    if (rc >= 0) {
        rc = (inflate)(&zstream, Z_FINISH);

        if (rc >= 0) {
            rc = (inflateEnd)(&zstream);
        }
        else {
            OTHERERROR("Error %d from inflate: %s\n", rc, zstream.msg);
            return NULL;
        }
    }
    else {
        OTHERERROR("Error %d from inflateInit: %s\n", rc, zstream.msg);
        return NULL;
    }

    return out;
}

/*
 * Extract an archive entry.
 * Returns pointer to the data (must be freed).
 */
unsigned char *
pyi_arch_extract(ARCHIVE_STATUS *status, TOC *ptoc)
{
    unsigned char *data;
    unsigned char *tmp;

    if (pyi_arch_open_fp(status) != 0) {
        OTHERERROR("Cannot open archive file\n");
        return NULL;
    }

    fseek(status->fp, status->pkgstart + ntohl(ptoc->pos), SEEK_SET);
    data = (unsigned char *)malloc(ntohl(ptoc->len));

    if (data == NULL) {
        OTHERERROR("Could not allocate read buffer\n");
        return NULL;
    }

    if (fread(data, ntohl(ptoc->len), 1, status->fp) < 1) {
        OTHERERROR("Could not read from file\n");
        free(data);
        return NULL;
    }

    if (ptoc->cflag == '\1') {
        tmp = decompress(data, ptoc);
        free(data);
        data = tmp;

        if (data == NULL) {
            OTHERERROR("Error decompressing %s\n", ptoc->name);
            return NULL;
        }
    }

    pyi_arch_close_fp(status);
    return data;
}

/*
 * Extract from the archive and copy to the filesystem.
 * The path is relative to the directory the archive is in.
 */
int
pyi_arch_extract2fs(ARCHIVE_STATUS *status, TOC *ptoc)
{
    FILE *out;
    size_t result, len;
    unsigned char *data = pyi_arch_extract(status, ptoc);

    /* Create tmp dir _MEIPASSxxx. */
    if (pyi_create_temp_path(status) == -1) {
        return -1;
    }

    out = pyi_open_target(status->temppath, ptoc->name);
    len = ntohl(ptoc->ulen);

    if (out == NULL) {
        FATAL_PERROR("fopen", "%s could not be extracted!\n", ptoc->name);
        return -1;
    }
    else {
        result = fwrite(data, len, 1, out);

        if ((1 != result) && (len > 0)) {
            FATAL_PERROR("fwrite", "Failed to write all bytes for %s\n", ptoc->name);
            return -1;
        }
#ifndef WIN32
        fchmod(fileno(out), S_IRUSR | S_IWUSR | S_IXUSR);
#endif
        fclose(out);
    }
    free(data);

    return 0;
}

/*
 * Look for the predefined string MAGIC in the embedded data before the given
 * search end position. If MAGIC is found, copies the entire COOKIE struct into
 * status->cookie, sets status->pkgstart to the location of the archive and returns 0.
 * Returns -1 on failure.
 *
 * PyInstaller sets this cookie to a constant value. Bootloader
 * compares it with the expected value. If there is match then
 * bootloader knows where the data was embedded correctly.
 *
 * The search space uses the given sizes because on Windows and OS X, the code signing
 * will add padding between the end of the COOKIE and the beginning of the signature
 * to align the signature to a quadword or a page boundary respectively. On Linux,
 * we use objtool to insert the archive into the bootloader and on runtime parse the
 * ELF headers to extract the precise end offset. On other Unixes we search backwards
 * from the end of the file.
 */
#if defined(WIN32)
#define SEARCH_SIZE (8 + sizeof(COOKIE))
#elif defined(__linux__)
#define SEARCH_SIZE (sizeof(COOKIE))
#else
#define SEARCH_SIZE (4096 + sizeof(COOKIE))
#endif

static int
pyi_arch_find_cookie(ARCHIVE_STATUS *status, int search_end)
{
    int search_start = search_end - SEARCH_SIZE;
    char buf[SEARCH_SIZE];
    char * search_ptr = buf + SEARCH_SIZE - sizeof(COOKIE);

    if (fseek(status->fp, search_start, SEEK_SET)) {
        return -1;
    }

    /* Read the entire search space */
    if (fread(buf, SEARCH_SIZE, 1, status->fp) < 1) {
        return -1;
    }

    /* Search for MAGIC within search space */

    while(search_ptr >= buf) {
        if(0 == strncmp(MAGIC, search_ptr, strlen(MAGIC))) {
            /* MAGIC found - Copy COOKIE to status->cookie */
            memcpy(&status->cookie, search_ptr, sizeof(COOKIE));

            /* From the cookie, calculate the archive start */
            status->pkgstart = search_start + sizeof(COOKIE) + (search_ptr - buf) - ntohl(status->cookie.len);

            return 0;
        }
        search_ptr--;
    }

    return -1;
}

static int
findDigitalSignature(ARCHIVE_STATUS * const status)
{
#ifdef _WIN32
    /* There might be a digital signature attached. Let's see. */
    char buf[2];
    int offset = 0, signature_offset = 0;
    fseek(status->fp, 0, SEEK_SET);
    fread(buf, 1, 2, status->fp);

    if (!(buf[0] == 'M' && buf[1] == 'Z')) {
        return -1;
    }
    /* Skip MSDOS header */
    fseek(status->fp, 60, SEEK_SET);
    /* Read offset to PE header */
    fread(&offset, 4, 1, status->fp);
    fseek(status->fp, offset + 24, SEEK_SET);
    fread(buf, 2, 1, status->fp);

    if (buf[0] == 0x0b && buf[1] == 0x01) {
        /* 32 bit binary */
        signature_offset = 152;
    }
    else if (buf[0] == 0x0b && buf[1] == 0x02) {
        /* 64 bit binary */
        signature_offset = 168;
    }
    else {
        /* Invalid magic value */
        VS("LOADER: Could not find a valid magic value (was %x %x).\n",
           (unsigned int) buf[0], (unsigned int) buf[1]);
        return -1;
    }

    /* Jump to the fields that contain digital signature info */
    fseek(status->fp, offset + signature_offset, SEEK_SET);
    fread(&offset, 4, 1, status->fp);

    if (offset == 0) {
        return -1;
    }
    VS("LOADER: %s contains a digital signature\n", status->archivename);
    return offset;
#elif defined(__APPLE__)
    /* We inspect the Mach-O header to find a code signature
     *  https://developer.apple.com/library/mac/documentation/DeveloperTools/Conceptual/MachORuntime/
     *  1) Determine the length of the header
     *  2) Read the Mach-O Header to determine how many commands there are
     *  3) Read through the commands and look for a code signature section (command #29)
     *  4) If we find a one, return where it starts */

    uint32_t magic_value;
    uint32_t header_size;

    uint32_t load_size;
    uint32_t cmd;
    uint32_t cmd_size;
    uint32_t offset = -1;

    /* The first 4 bytes determine the header length */
    fseek(status->fp, 0, SEEK_SET);
    fread(&magic_value, sizeof(uint32_t), 1, status->fp);

    if (magic_value == 0xfeedface || magic_value == 0xcefaedfe) {
        /* 32-bit, so the header size is 28 bytes. */
        header_size = 28;
    }
    else {
        /* 64-bit, so the header size is 32 bytes. */
        header_size = 32;
    }

    /* Determine the total size of all load commands */
    fseek(status->fp, 20, SEEK_SET);
    fread(&load_size, sizeof(uint32_t), 1, status->fp);

    fseek(status->fp, header_size, SEEK_SET);

    while (ftell(status->fp) < (header_size + load_size)) {
        fread(&cmd, sizeof(uint32_t), 1, status->fp);
        fread(&cmd_size, sizeof(uint32_t), 1, status->fp);

        if (cmd == 29) {
            /* Code signatures are command 29.
             *  Our archive ends right before the signature */
            fread(&offset, sizeof(uint32_t), 1, status->fp);
            VS("LOADER: %s contains a digital signature\n", status->archivename);
            break;
        }
        fseek(status->fp, cmd_size - 8, SEEK_CUR);
    }
    return offset;
#else /* ifdef _WIN32 */
    return -1;
#endif /* ifdef _WIN32 */
}

/*
 * Try to find the pydata section in an ELF executable.
 * Returns the end of the section if found.
 */
#ifdef __linux__
static int
findElfSection(ARCHIVE_STATUS * const status)
{
    char head[64];
    const uint16_t endianess_bytes = 0x0201;
    bool is64bit;
    uint64_t e_shoff;
    uint16_t e_shentsize;
    uint16_t e_shnum;
    uint16_t e_shstrndx;
    char *section;
    uint64_t shstr_offset;
    uint64_t shstr_size;
    char *shstr;
    uint32_t section_idx;
    uint64_t pydata_offset;
    uint64_t pydata_size;

    int rc = -1;

    fseek(status->fp, 0, SEEK_SET);
    if (fread(head, 64, 1, status->fp) != 1) {
        goto done;
    }

    /* Check if ELF magic present */
    if (head[0] != 0x7F || head[1] != 'E' || head[2] != 'L' || head[3] != 'F') {
        VS("LOADER: %s is not an ELF binary\n", status->archivename);
        goto done;
    }

    /* Ensure endianess of file matches */
    if (head[0x05] != *(uint8_t*)&endianess_bytes) {
        VS("LOADER: %s endianess does not match CPU\n", status->archivename);
        goto done;
    }

    /* Ensure ELF version is supported */
    if (head[0x06] != 1 || *(uint32_t*)(head + 0x14) != 1) {
        VS("LOADER: %s has an unknown ELF version\n", status->archivename);
        goto done;
    }

    /* Load ELF section header parameters */
    is64bit = head[0x04] == 2;
    if (is64bit) {
        e_shoff = *(uint64_t*)(head + 0x28);
        e_shentsize = *(uint16_t*)(head + 0x3a);
        e_shnum = *(uint16_t*)(head + 0x3c);
        e_shstrndx = *(uint16_t*)(head + 0x3e);
    } else {
        e_shoff = *(uint32_t*)(head + 0x20);
        e_shentsize = *(uint16_t*)(head + 0x2e);
        e_shnum = *(uint16_t*)(head + 0x30);
        e_shstrndx = *(uint16_t*)(head + 0x32);
    }

    section = malloc(e_shentsize);
    if (section == NULL) {
        FATAL_PERROR("malloc", "Could not allocate buffer for section header.");
        goto done;
    }

    /* Load shstr section into buffer */
    fseek(status->fp, e_shoff + e_shentsize * e_shstrndx, SEEK_SET);
    if (fread(section, e_shentsize, 1, status->fp) != 1) {
        VS("LOADER: %s could not read shstr section header\n", status->archivename);
        goto cleanup_section;
    }

    if (is64bit) {
        shstr_offset = *(uint64_t*)(section + 0x18);
        shstr_size = *(uint64_t*)(section + 0x20);
    } else {
        shstr_offset = *(uint32_t*)(section + 0x10);
        shstr_size = *(uint32_t*)(section + 0x14);
    }

    shstr = malloc(shstr_size);
    if (shstr == NULL) {
        FATAL_PERROR("malloc", "Could not allocate buffer for ELF shstrs.");
        goto cleanup_section;
    }

    fseek(status->fp, shstr_offset, SEEK_SET);
    if (fread(shstr, shstr_size, 1, status->fp) != 1) {
        VS("LOADER: %s could not read shstr section\n", status->archivename);
        goto cleanup_shstr;
    }

    /* Find section named "pydata" */
    for (section_idx=0; section_idx<e_shnum; section_idx++) {
        uint32_t name_offset;

        fseek(status->fp, e_shoff + e_shentsize * section_idx, SEEK_SET);
        if (fread(section, e_shentsize, 1, status->fp) != 1) {
            VS("LOADER: %s could not read section header\n", status->archivename);
            goto cleanup_shstr;
        }

        name_offset = *(uint32_t*)(section);
        if (!strncmp(shstr + name_offset, "pydata", shstr_size-name_offset)) {
            break;
        }
    }

    if (section_idx == e_shnum) {
        VS("LOADER: %s could not find pydata section\n", status->archivename);
        goto cleanup_shstr;
    }

    /* Calculate and return end of section */
    if (is64bit) {
        pydata_offset = *(uint64_t*)(section + 0x18);
        pydata_size = *(uint64_t*)(section + 0x20);
    } else {
        pydata_offset = *(uint32_t*)(section + 0x10);
        pydata_size = *(uint32_t*)(section + 0x14);
    }

    /* Assign result if it fits into int */
    if (pydata_offset + pydata_size <= INT_MAX) {
        rc = pydata_offset + pydata_size;
    }

cleanup_shstr:
    free(shstr);
cleanup_section:
    free(section);
done:
    return rc;
}
#endif

/*
 * Open the archive.
 * Sets f_archiveFile, f_pkgstart, f_tocbuff and f_cookie.
 */
int
pyi_arch_open(ARCHIVE_STATUS *status)
{
    int search_end = 0;
    VS("LOADER: archivename is %s\n", status->archivename);

    /* Physically open the file */
    if (pyi_arch_open_fp(status) != 0) {
        VS("LOADER: Cannot open archive: %s\n", status->archivename);
        return -1;
    }

    /* Find out where to stop searching for the cookie. First try to find
     * a digital signature added by a code signing tool.
     */
#if defined(WIN32) || defined(__APPLE__)
    search_end = findDigitalSignature(status);
#elif defined(__linux__)
    search_end = findElfSection(status);
#endif

    /* Signature not found or not applicable for this platform. Stop searching
     * at end of file.
     */
    if (search_end < 1) {
        fseek(status->fp, 0, SEEK_END);
        search_end = ftell(status->fp);
    }

    /* Load status->cookie */
    if (-1 == pyi_arch_find_cookie(status, search_end)) {
        VS("Loader: Cannot find cookie");
        return -1;
    }

    /* Set the flag that Python library was not loaded yet. */
    status->is_pylib_loaded = false;

    /* Set the the Python version used. */
    pyvers = pyi_arch_get_pyversion(status);

    /* Read in in the table of contents */
    fseek(status->fp, status->pkgstart + ntohl(status->cookie.TOC), SEEK_SET);
    status->tocbuff = (TOC *) malloc(ntohl(status->cookie.TOClen));

    if (status->tocbuff == NULL) {
        FATAL_PERROR("malloc", "Could not allocate buffer for TOC.");
        return -1;
    }

    if (fread(status->tocbuff, ntohl(status->cookie.TOClen), 1, status->fp) < 1) {
        FATAL_PERROR("fread", "Could not read from file.");
        return -1;
    }
    status->tocend = (TOC *) (((char *)status->tocbuff) + ntohl(status->cookie.TOClen));

    /* Check input file is still ok (should be). */
    if (ferror(status->fp)) {
        FATALERROR("Error on file\n.");
        return -1;
    }

    /* Close file handler
     * if file not close here it will be close in pyi_arch_status_free_memory */
    pyi_arch_close_fp(status);
    return 0;
}

/*
 * Set up paths required by rest of this module.
 * Sets f_archivename, f_homepath, f_mainpath
 */
int
pyi_arch_set_paths(ARCHIVE_STATUS *status, char const * archivePath,
                   char const * archiveName)
{
    size_t pathlen, namelen;

    pathlen = strnlen(archivePath, PATH_MAX);
    namelen = strnlen(archiveName, PATH_MAX);

    if (pathlen+namelen+1 > PATH_MAX) {
        return -1;
    }

    /* Get the archive Path */
    strcpy(status->archivename, archivePath);
    strcat(status->archivename, archiveName);

    /* Set homepath to where the archive is */
    strcpy(status->homepath, archivePath);

    /*
     * Initial value of mainpath is homepath. It might be overriden
     * by temppath if it is available.
     */
    status->has_temp_directory = false;
    strcpy(status->mainpath, status->homepath);

    return 0;
}

/* Setup the archive with python modules. (this always needs to be done) */
int
pyi_arch_setup(ARCHIVE_STATUS *status, char const * archivePath, char const * archiveName)
{
    /* Set up paths */
    if (pyi_arch_set_paths(status, archivePath, archiveName)) {
        return -1;
    }

    /* Open the archive */
    if (pyi_arch_open(status)) {
        /* If this is not an archive, we MUST close the file, */
        /* otherwise the open file-handle will be reused when */
        /* testing the next file. */
        pyi_arch_close_fp(status);
        return -1;
    }
    ;
    return 0;
}

/*
 * external API for iterating TOCs
 */
TOC *
getFirstTocEntry(ARCHIVE_STATUS *status)
{
    return status->tocbuff;
}
TOC *
getNextTocEntry(ARCHIVE_STATUS *status, TOC *entry)
{
    TOC *rslt = (TOC*)((char *)entry + ntohl(entry->structlen));

    if (rslt >= status->tocend) {
        return NULL;
    }
    return rslt;
}

/*
 * Helpers for embedders.
 */
int
pyi_arch_get_pyversion(ARCHIVE_STATUS *status)
{
    return ntohl(status->cookie.pyvers);
}

/*
 * Free memory allocated for archive status.
 */
void
pyi_arch_status_free_memory(ARCHIVE_STATUS *archive_status)
{
    if (archive_status != NULL) {
        VS("LOADER: Freeing archive status for %s\n", archive_status->archivename);

        /* Free the TOC memory from the archive status first. */
        if (archive_status->tocbuff != NULL) {
            free(archive_status->tocbuff);
        }
        /* Close file handler */
        pyi_arch_close_fp(archive_status);
        free(archive_status);
    }
}

/*
 * Returns the value of the pyi bootloader option given by optname. Returns
 * NULL if the option is not present. Returns an empty string if the option is present,
 * but has no associated value.
 *
 * The string returned is owned by the ARCHIVE_STATUS; the caller is NOT responsible
 * for freeing it.
 */
char *
pyi_arch_get_option(const ARCHIVE_STATUS * status, char * optname)
{
    /* TODO: option-cache? */
    int optlen;
    TOC *ptoc = status->tocbuff;

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
