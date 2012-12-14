/*
 * Fuctions related to PyInstaller archive embedded in executable.
 *
 * Copyright (C) 2012, Martin Zibricky
 * Copyright (C) 2005-2011, Giovanni Bajo
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


#ifdef WIN32
// TODO verify windows includes
    #include <winsock.h>  // ntohl
#else
    #include <limits.h>  // PATH_MAX - not available on windows.
    #include <netinet/in.h>  // ntohl
    #include <sys/stat.h>  // fchmod
#endif
#include <stddef.h>  // ptrdiff_t
#include <stdio.h>


/* PyInstaller headers. */
#include "zlib.h"
#include "stb.h"
#include "pyi_global.h"
#include "pyi_archive.h"
#include "pyi_utils.h"
#include "pyi_python.h"


/* Magic number to verify archive data are bundled correctly. */
#define MAGIC "MEI\014\013\012\013\016"


/*
 * Return pointer to next toc entry.
 */
TOC *pyi_arch_increment_toc_ptr(ARCHIVE_STATUS *status, TOC* ptoc)
{
	TOC *result = (TOC*)((char *)ptoc + ntohl(ptoc->structlen));
	if (result < status->tocbuff) {
		FATALERROR("Cannot read Table of Contents.\n");
		return status->tocend;
	}
	return result;
}


/* 
 * Decompress data in buff, described by ptoc.
 * Return in malloc'ed buffer (needs to be freed)
 */
static unsigned char *decompress(unsigned char * buff, TOC *ptoc)
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
unsigned char *pyi_arch_extract(ARCHIVE_STATUS *status, TOC *ptoc)
{
	unsigned char *data;
	unsigned char *tmp;

	fseek(status->fp, status->pkgstart + ntohl(ptoc->pos), SEEK_SET);
	data = (unsigned char *)malloc(ntohl(ptoc->len));
	if (data == NULL) {
		OTHERERROR("Could not allocate read buffer\n");
		return NULL;
	}
	if (fread(data, ntohl(ptoc->len), 1, status->fp) < 1) {
	    OTHERERROR("Could not read from file\n");
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
	return data;
}


/*
 * Extract from the archive and copy to the filesystem.
 * The path is relative to the directory the archive is in.
 */
int pyi_arch_extract2fs(ARCHIVE_STATUS *status, TOC *ptoc)
{
	FILE *out;
	unsigned char *data = pyi_arch_extract(status, ptoc);

    if (pyi_create_temp_path(status) == -1){
        return -1;
    }

	out = pyi_open_target(status->temppath, ptoc->name);

	if (out == NULL)  {
		FATALERROR("%s could not be extracted!\n", ptoc->name);
		return -1;
	}
	else {
		fwrite(data, ntohl(ptoc->ulen), 1, out);
#ifndef WIN32
		fchmod(fileno(out), S_IRUSR | S_IWUSR | S_IXUSR);
#endif
		fclose(out);
	}
	free(data);
	return 0;
}


/*
 * Look for a predefined value in the embedded data.
 *
 * PyInstaller sets this cookie to a constant value. Bootloader
 * compares it with the expected value. If there is match then
 * bootloader knows the data was embedded correctly.
 */
static int pyi_arch_check_cookie(ARCHIVE_STATUS *status, int filelen)
{
	if (fseek(status->fp, filelen-(int)sizeof(COOKIE), SEEK_SET))
		return -1;

	/* Read the Cookie, and check its MAGIC bytes */
	if (fread(&(status->cookie), sizeof(COOKIE), 1, status->fp) < 1)
	    return -1;
	if (strncmp(status->cookie.magic, MAGIC, strlen(MAGIC)))
		return -1;

  return 0;
}


static int findDigitalSignature(ARCHIVE_STATUS * const status)
{
#ifdef WIN32
	/* There might be a digital signature attached. Let's see. */
	char buf[2];
	int offset = 0, signature_offset = 0;
	fseek(status->fp, 0, SEEK_SET);
	fread(buf, 1, 2, status->fp);
	if (!(buf[0] == 'M' && buf[1] == 'Z'))
		return -1;
	/* Skip MSDOS header */
	fseek(status->fp, 60, SEEK_SET);
	/* Read offset to PE header */
	fread(&offset, 4, 1, status->fp);
	fseek(status->fp, offset+24, SEEK_SET);
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
          VS("Could not find a valid magic value (was %x %x).\n", (unsigned int) buf[0], (unsigned int) buf[1]);
          return -1;
        }

	/* Jump to the fields that contain digital signature info */
	fseek(status->fp, offset+signature_offset, SEEK_SET);
	fread(&offset, 4, 1, status->fp);
	if (offset == 0)
		return -1;
  VS("%s contains a digital signature\n", status->archivename);
	return offset;
#else
	return -1;
#endif
}


/*
 * Open the archive.
 * Sets f_archiveFile, f_pkgstart, f_tocbuff and f_cookie.
 */
int pyi_arch_open(ARCHIVE_STATUS *status)
{
#ifdef WIN32
	int i;
#endif
	int filelen;
    VS("archivename is %s\n", status->archivename);
	/* Physically open the file */
	status->fp = stb_fopen(status->archivename, "rb");
	if (status->fp == NULL) {
		VS("Cannot open archive: %s\n", status->archivename);
		return -1;
	}

	/* Seek to the Cookie at the end of the file. */
	fseek(status->fp, 0, SEEK_END);
	filelen = ftell(status->fp);

	if (pyi_arch_check_cookie(status, filelen) < 0)
	{
		VS("%s does not contain an embedded package\n", status->archivename);
#ifndef WIN32
    return -1;
#else
		filelen = findDigitalSignature(status);
		if (filelen < 1)
			return -1;
		/* The digital signature has been aligned to 8-bytes boundary.
		   We need to look for our cookie taking into account some
		   padding. */
		for (i = 0; i < 8; ++i)
		{
			if (pyi_arch_check_cookie(status, filelen) >= 0)
				break;
			--filelen;
		}
		if (i == 8)
		{
			VS("%s does not contain an embedded package, even skipping the signature\n", status->archivename);
			return -1;
		}
		VS("package found skipping digital signature in %s\n", status->archivename);
#endif
	}

	/* From the cookie, calculate the archive start */
	status->pkgstart = filelen - ntohl(status->cookie.len);

	/* Read in in the table of contents */
	fseek(status->fp, status->pkgstart + ntohl(status->cookie.TOC), SEEK_SET);
	status->tocbuff = (TOC *) malloc(ntohl(status->cookie.TOClen));
	if (status->tocbuff == NULL)
	{
		FATALERROR("Could not allocate buffer for TOC.");
		return -1;
	}
	if (fread(status->tocbuff, ntohl(status->cookie.TOClen), 1, status->fp) < 1)
	{
	    FATALERROR("Could not read from file.");
	    return -1;
	}
	status->tocend = (TOC *) (((char *)status->tocbuff) + ntohl(status->cookie.TOClen));

	/* Check input file is still ok (should be). */
	if (ferror(status->fp))
	{
		FATALERROR("Error on file");
		return -1;
	}
	return 0;
}


/*
 * Set up paths required by rest of this module.
 * Sets f_archivename, f_homepath, f_mainpath
 */
int pyi_arch_set_paths(ARCHIVE_STATUS *status, char const * archivePath, char const * archiveName)
{
#ifdef WIN32
	char *p;
#endif
	/* Get the archive Path */
	strcpy(status->archivename, archivePath);
	strcat(status->archivename, archiveName);

	/* Set homepath to where the archive is */
	strcpy(status->homepath, archivePath);
#ifdef WIN32
    /* Replace backslashes with forward slashes. */
    // TODO eliminate the need for this conversion and homepathraw and temppathraw
	strcpy(status->homepathraw, archivePath);
	for ( p = status->homepath; *p; p++ )
		if (*p == '\\')
			*p = '/';
#endif

    /*
     * Initial value of mainpath is homepath. It might be overriden
     * by temppath if it is available.
     */
    status->has_temp_directory = false;
#ifdef WIN32
	strcpy(status->mainpath, status->homepathraw);
#else
	strcpy(status->mainpath, status->homepath);
#endif

	return 0;
}



/*
 * external API for iterating TOCs
 */
TOC *getFirstTocEntry(ARCHIVE_STATUS *status)
{
	return status->tocbuff;
}
TOC *getNextTocEntry(ARCHIVE_STATUS *status, TOC *entry)
{
	TOC *rslt = (TOC*)((char *)entry + ntohl(entry->structlen));
	if (rslt >= status->tocend)
		return NULL;
	return rslt;
}


/*
 * Helpers for embedders.
 */
int pyi_arch_get_pyversion(ARCHIVE_STATUS *status)
{
	return ntohl(status->cookie.pyvers);
}
