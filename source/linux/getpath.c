/***********************************************************
Copyright 1991-1995 by Stichting Mathematisch Centrum, Amsterdam,
The Netherlands.

                        All Rights Reserved

Permission to use, copy, modify, and distribute this software and its
documentation for any purpose and without fee is hereby granted,
provided that the above copyright notice appear in all copies and that
both that copyright notice and this permission notice appear in
supporting documentation, and that the names of Stichting Mathematisch
Centrum or CWI or Corporation for National Research Initiatives or
CNRI not be used in advertising or publicity pertaining to
distribution of the software without specific, written prior
permission.

While CWI is the initial source for this software, a modified version
is made available by the Corporation for National Research Initiatives
(CNRI) at the Internet address ftp://ftp.python.org.

STICHTING MATHEMATISCH CENTRUM AND CNRI DISCLAIM ALL WARRANTIES WITH
REGARD TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS, IN NO EVENT SHALL STICHTING MATHEMATISCH
CENTRUM OR CNRI BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL
DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR
PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER
TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
PERFORMANCE OF THIS SOFTWARE.

******************************************************************/

/* A special version for minimal installs, where
   the bootstrap path is the directory in which
   the executable lives.
   Gordon McMillan, McMillan Enterprises, Inc. */

/* Return the initial module search path. */

#include "getpath.h"
#include "osdefs.h"

#include <sys/types.h>
#include <sys/stat.h>
#include <string.h>
#include <stdlib.h>     /* getenv */
#include <stdio.h>      /* sprintf */
#include <unistd.h>     /* readlink */

static char prefix[MAXPATHLEN+1];
static char *exec_prefix;
static char progpath[MAXPATHLEN+1];
static char *module_search_path = NULL;

static void
reduce(char *dir)
{
	int i = strlen(dir);
	while (i > 0 && dir[i] != SEP)
		--i;
	dir[i] = '\0';
}


#ifndef S_ISREG
#define S_ISREG(x) (((x) & S_IFMT) == S_IFREG)
#endif

#ifndef S_ISDIR
#define S_ISDIR(x) (((x) & S_IFMT) == S_IFDIR)
#endif
#if 0
static int
isfile(char *filename)		/* Is file, not directory */
{
	struct stat buf;
	if (stat(filename, &buf) != 0)
		return 0;
	if (!S_ISREG(buf.st_mode))
		return 0;
	return 1;
}
#endif
#if 0
static int
ismodule(char *filename)		/* Is module -- check for .pyc/.pyo too */
{
	if (isfile(filename))
		return 1;

	/* Check for the compiled version of prefix. */
	if (strlen(filename) < MAXPATHLEN) {
		strcat(filename, Py_OptimizeFlag ? "o" : "c");
		if (isfile(filename))
			return 1;
	}
	return 0;
}
#endif

static int
isxfile(char *filename)		/* Is executable file */
{
	struct stat buf;
	if (stat(filename, &buf) != 0)
		return 0;
	if (!S_ISREG(buf.st_mode))
		return 0;
	if ((buf.st_mode & 0111) == 0)
		return 0;
	return 1;
}

#if 0
static int
isdir(char *filename)			/* Is directory */
{
	struct stat buf;
	if (stat(filename, &buf) != 0)
		return 0;
	if (!S_ISDIR(buf.st_mode))
		return 0;
	return 1;
}
#endif

static void
joinpath(char *buffer, char *stuff)
{
	int n, k;
	if (stuff[0] == SEP)
		n = 0;
	else {
		n = strlen(buffer);
		if (n > 0 && buffer[n-1] != SEP && n < MAXPATHLEN)
			buffer[n++] = SEP;
	}
	k = strlen(stuff);
	if (n + k > MAXPATHLEN)
		k = MAXPATHLEN - n;
	strncpy(buffer+n, stuff, k);
	buffer[n+k] = '\0';
}

static void
calculate_path(void)
{
	char *prog = PI_GetProgramName();	/* use Py_SetProgramName(argv[0]) before Py_Initialize() */
	char argv0_path[MAXPATHLEN+1];
	char *epath;
	char *path = NULL;
	char *ppath = NULL;
#if HAVE_READLINK
	int  numchars;
#endif

	if (strchr(prog, SEP))
		strcpy(progpath, prog);
	else {
#if HAVE_READLINK
            sprintf(argv0_path, "/proc/%d/exe", getpid());
            numchars = readlink(argv0_path, progpath, MAXPATHLEN);
            if (numchars > 0) 
                progpath[numchars] = '\0';
            else {
#endif
		epath = getenv("PATH");
                if (epath) 
                    path = malloc(strlen(epath)+3);
		if (path) {
                    strcpy(path, ".:");
                    strcat(path, epath);
		    ppath = path;
	    	    while (1) {
				char *delim = strchr(ppath, DELIM);

				if (delim) {
					int len = delim - ppath;
					strncpy(progpath, ppath, len);
					*(progpath + len) = '\0';
				}
				else
					strcpy(progpath, ppath);

				joinpath(progpath, prog);
				if (isxfile(progpath))
					break;

				if (!delim) {
					progpath[0] = '\0';
					break;
				}
				ppath = delim + 1;
		    }
                    free(path);
		}
		else
			progpath[0] = '\0';
#if HAVE_READLINK
            }
#endif
	}
	/* at this point progpath includes the executable */
	strcpy(argv0_path, progpath);
	
#if HAVE_READLINK
	{
		char tmpbuffer[MAXPATHLEN+1];
		int linklen = readlink(progpath, tmpbuffer, MAXPATHLEN);
		while (linklen != -1) {
			/* It's not null terminated! */
			tmpbuffer[linklen] = '\0';
			if (tmpbuffer[0] == SEP)
				strcpy(argv0_path, tmpbuffer);
			else {
				/* Interpret relative to progpath */
				reduce(argv0_path);
				joinpath(argv0_path, tmpbuffer);
			}
			linklen = readlink(argv0_path, tmpbuffer, MAXPATHLEN);
		}
                strcpy(progpath, argv0_path);
	}
#endif /* HAVE_READLINK */

	reduce(argv0_path);
	/* now argv0_path is the directory of the executable */

	strcpy(prefix, argv0_path);
	exec_prefix = prefix;
	module_search_path = malloc(strlen(prefix)+1);
	strcpy(module_search_path, prefix);

}
/* External interface */

static char *progname = "python";

void
PI_SetProgramName(char *pn)
{
	if (pn && *pn)
		progname = pn;
}

char *
PI_GetProgramName(void)
{
	return progname;
}

char *
PI_GetPath(void)
{
	if (!module_search_path)
		calculate_path();
	return module_search_path;
}

char *
PI_GetPrefix(void)
{
	if (!module_search_path)
		calculate_path();
	return prefix;
}

char *
PI_GetExecPrefix(void)
{
	if (!module_search_path)
		calculate_path();
	return exec_prefix;
}

char *
PI_GetProgramFullPath(void)
{
	if (!module_search_path)
		calculate_path();
	return progpath;
}
