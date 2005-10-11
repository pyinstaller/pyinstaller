/*
 * Minimal C library for the bootloader (to not depend on MSVCRT)
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

#define _CRTIMP
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#define WIN32_LEAN_AND_MEAN
#include <windows.h>

int mkdir(const char *path)
{
	if (!CreateDirectory((LPTSTR)path, (LPSECURITY_ATTRIBUTES)NULL))
		return -1;
	return 0;
}

char *strcat(char *dst, const char * src)
{
	return lstrcat(dst, src);
}

size_t strlen(const char * str)
{
	return lstrlen(str);
}

char *strcpy(char * dst, const char *src)
{
	return lstrcpy(dst, src);
}

int strcmp(const char * src1, const char *src2)
{
	return lstrcmp(src1, src2);
}

int strncmp(const char * first, const char * last, size_t count)
{
	return 0;
}

void *memcpy(void *dst, const void *src, size_t count)
{
	void *ret = dst;

	while (count--)
	{
		*(char *)dst = *(char *)src;
		dst = (char *)dst + 1;
		src = (char *)src + 1;
	}

	return dst;
}

void *memset(void *dst, int val, size_t count)
{
	void *ret = dst;

	while (count--)
	{
		*(char *)dst = (char)val;
		dst = (char *)dst + 1;
	}

	return ret;
}

/*
int remove(const char *path)
{
	if (!DeleteFile((LPTSTR)path))
		return -1;
	return 0;
}

int rmdir(const char *path)
{
	if (!RemoveDirectory((LPTSTR)path))
		return -1;
	return 0;
}
*/

int sprintf(char *buf, const char *fmt, ...)
{
	va_list v;
	int ret;

	va_start(v, fmt);
	ret = wvsprintf(buf, fmt, v);
	va_end(v);
	return ret;
}

static HANDLE g_confh = (HANDLE)-2;

static void initConsole(void)
{
	g_confh = (HANDLE)CreateFile( "CONOUT$",
		GENERIC_WRITE,
		FILE_SHARE_READ | FILE_SHARE_WRITE,
		NULL,
		OPEN_EXISTING,
		0,
		NULL );
}

int printf(const char *fmt, ...)
{
	char buf[1024];
	int num;
	DWORD numwritten;

	va_list v;
	va_start(v, fmt);
	num = wvsprintf(buf, fmt, v);
	va_end(v);

	if (g_confh == (HANDLE)-2)
		initConsole();

	WriteConsole(g_confh, buf, num, &numwritten, NULL);

	return num;
}

int getpid(void)
{
	return GetCurrentProcessId();
}

void *malloc(size_t size)
{
	return (void*)GlobalAlloc(GMEM_FIXED, size);
}

void free(void *buf)
{
	GlobalFree((HGLOBAL)buf);
}

