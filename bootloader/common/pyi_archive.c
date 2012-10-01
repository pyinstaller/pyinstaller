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

// TODO leave only necessary header includes.
#include <stdio.h>
#ifdef WIN32
 #include <windows.h>
 #include <direct.h>
 #include <process.h>
 #include <io.h>
#else
 #include <unistd.h>
 #include <fcntl.h>
 #include <dlfcn.h>
 #include <dirent.h>
 #include <stdarg.h>
#endif
#include <sys/types.h>
#include <sys/stat.h>
#include "launch.h"
#include <string.h>
#include "zlib.h"

#include "pyi_utils.h"
#include "pyi_python.h"
#include "pyi_archive.h"


/*
 * Return pointer to next toc entry.
 */
TOC *incrementTocPtr(ARCHIVE_STATUS *status, TOC* ptoc)
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
unsigned char *extract(ARCHIVE_STATUS *status, TOC *ptoc)
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
	if (ptoc->cflag == '\2') {
        static PyObject *AES = NULL;
		PyObject *func_new;
		PyObject *aes_dict;
		PyObject *aes_obj;
		PyObject *ddata;
		long block_size;
		char *iv;

		if (!AES)
			AES = PI_PyImport_ImportModule("AES");
		aes_dict = PI_PyModule_GetDict(AES);
		func_new = PI_PyDict_GetItemString(aes_dict, "new");
		block_size = PI_PyInt_AsLong(PI_PyDict_GetItemString(aes_dict, "block_size"));
		iv = malloc(block_size);
		memset(iv, 0, block_size);

		aes_obj = PI_PyObject_CallFunction(func_new, "s#Os#",
			data, 32,
			PI_PyDict_GetItemString(aes_dict, "MODE_CFB"),
			iv, block_size);

		ddata = PI_PyObject_CallMethod(aes_obj, "decrypt", "s#", data+32, ntohl(ptoc->len)-32);
		memcpy(data, PI_PyString_AsString(ddata), ntohl(ptoc->len)-32);
		Py_DECREF(aes_obj);
		Py_DECREF(ddata);
		VS("decrypted %s\n", ptoc->name);
	}
	if (ptoc->cflag == '\1' || ptoc->cflag == '\2') {
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
int extract2fs(ARCHIVE_STATUS *status, TOC *ptoc)
{
	FILE *out;
	unsigned char *data = extract(status, ptoc);

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
