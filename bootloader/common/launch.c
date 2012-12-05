/*
 * Launch a python module from an archive.
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
    #include <windows.h>
#else
    #include <limits.h>  // PATH_MAX
#endif
#include <stdarg.h>
#include <stddef.h>  // ptrdiff_t
#include <stdio.h>  // vsnprintf
#include <sys/stat.h>  // struct stat


/* PyInstaller headers. */
#include "stb.h"
#include "pyi_global.h"
#include "pyi_archive.h"
#include "pyi_utils.h"
#include "pyi_python.h"
#include "pyi_pythonlib.h"


/*
 * The functions in this file defined in reverse order so that forward
 * declarations are not necessary.
 */


static int checkFile(char *buf, const char *fmt, ...)
{
    va_list args;
    struct stat tmp;

    va_start(args, fmt);
    vsnprintf(buf, PATH_MAX, fmt, args);
    va_end(args);

    return stat(buf, &tmp);
}



/* Splits the item in the form path:filename */
static int splitName(char *path, char *filename, const char *item)
{
    char name[PATH_MAX + 1];

    VS("Splitting item into path and filename\n");
    strcpy(name, item);
    strcpy(path, strtok(name, ":"));
    strcpy(filename, strtok(NULL, ":")) ;

    if (path[0] == 0 || filename[0] == 0)
        return -1;
    return 0;
}

/* Copy the dependencies file from a directory to the tempdir */
static int copyDependencyFromDir(ARCHIVE_STATUS *status, const char *srcpath, const char *filename)
{
    if (pyi_create_temp_path(status) == -1){
        return -1;
    }

    VS("Coping file %s to %s\n", srcpath, status->temppath);
    if (pyi_copy_file(srcpath, status->temppath, filename) == -1) {
        return -1;
    }
    return 0;
}

/* Look for the archive identified by path into the ARCHIVE_STATUS pool status_list.
 * If the archive is found, a pointer to the associated ARCHIVE_STATUS is returned
 * otherwise the needed archive is opened and added to the pool and then returned.
 * If an error occurs, returns NULL.
 */
static ARCHIVE_STATUS *get_archive(ARCHIVE_STATUS *status_list[], const char *path)
{
    ARCHIVE_STATUS *status = NULL;
    int i = 0;

    VS("Getting file from archive.\n");
    if (pyi_create_temp_path(status_list[SELF]) == -1){
        return NULL;
    }

    for (i = 1; status_list[i] != NULL; i++){
        if (strcmp(status_list[i]->archivename, path) == 0) {
            VS("Archive found: %s\n", path);
            return status_list[i];
        }
        VS("Checking next archive in the list...\n");
    }

    if ((status = (ARCHIVE_STATUS *) calloc(1, sizeof(ARCHIVE_STATUS))) == NULL) {
        FATALERROR("Error allocating memory for status\n");
        return NULL;
    }

    strcpy(status->archivename, path);
    strcpy(status->homepath, status_list[SELF]->homepath);
    strcpy(status->temppath, status_list[SELF]->temppath);
#ifdef WIN32
    strcpy(status->homepathraw, status_list[SELF]->homepathraw);
    strcpy(status->temppathraw, status_list[SELF]->temppathraw);
#endif

    if (pyi_arch_open(status)) {
        FATALERROR("Error openning archive %s\n", path);
        free(status);
        return NULL;
    }

    status_list[i] = status;
    return status;
}

/* Extract a file identifed by filename from the archive associated to status. */
static int extractDependencyFromArchive(ARCHIVE_STATUS *status, const char *filename)
{
	TOC * ptoc = status->tocbuff;
	VS("Extracting dependencies from archive\n");
	while (ptoc < status->tocend) {
		if (strcmp(ptoc->name, filename) == 0)
			if (pyi_arch_extract2fs(status, ptoc))
				return -1;
		ptoc = pyi_arch_increment_toc_ptr(status, ptoc);
	}
	return 0;
}

/* Decide if the dependency identified by item is in a onedir or onfile archive
 * then call the appropriate function.
 */
static int extractDependency(ARCHIVE_STATUS *status_list[], const char *item)
{
    ARCHIVE_STATUS *status = NULL;
    char path[PATH_MAX + 1];
    char filename[PATH_MAX + 1];
    char srcpath[PATH_MAX + 1];
    char archive_path[PATH_MAX + 1];

    char *dirname = NULL;

    VS("Extracting dependencies\n");
    if (splitName(path, filename, item) == -1)
        return -1;

    dirname = pyi_path_dirname(path);
    if (dirname[0] == 0) {
        free(dirname);
        return -1;
    }

    /* We need to identify three situations: 1) dependecies are in a onedir archive
     * next to the current onefile archive, 2) dependencies are in a onedir/onefile
     * archive next to the current onedir archive, 3) dependencies are in a onefile
     * archive next to the current onefile archive.
     */
    VS("Checking if file exists\n");
    if (checkFile(srcpath, "%s/%s/%s", status_list[SELF]->homepath, dirname, filename) == 0) {
        VS("File %s found, assuming is onedir\n", srcpath);
        if (copyDependencyFromDir(status_list[SELF], srcpath, filename) == -1) {
            FATALERROR("Error coping %s\n", filename);
            free(dirname);
            return -1;
        }
    } else if (checkFile(srcpath, "%s../%s/%s", status_list[SELF]->homepath, dirname, filename) == 0) {
        VS("File %s found, assuming is onedir\n", srcpath);
        if (copyDependencyFromDir(status_list[SELF], srcpath, filename) == -1) {
            FATALERROR("Error coping %s\n", filename);
            free(dirname);
            return -1;
        }
    } else {
        VS("File %s not found, assuming is onefile.\n", srcpath);
        if ((checkFile(archive_path, "%s%s.pkg", status_list[SELF]->homepath, path) != 0) &&
            (checkFile(archive_path, "%s%s.exe", status_list[SELF]->homepath, path) != 0) &&
            (checkFile(archive_path, "%s%s", status_list[SELF]->homepath, path) != 0)) {
            FATALERROR("Archive not found: %s\n", archive_path);
            return -1;
        }

        if ((status = get_archive(status_list, archive_path)) == NULL) {
            FATALERROR("Archive not found: %s\n", archive_path);
            return -1;
        }
        if (extractDependencyFromArchive(status, filename) == -1) {
            FATALERROR("Error extracting %s\n", filename);
            free(status);
            return -1;
        }
    }
    free(dirname);

    return 0;
}


/*
 * check if binaries need to be extracted. If not, this is probably a onedir solution,
 * and a child process will not be required on windows.
 */
int needToExtractBinaries(ARCHIVE_STATUS *status_list[])
{
	TOC * ptoc = status_list[SELF]->tocbuff;
	while (ptoc < status_list[SELF]->tocend) {
		if (ptoc->typcd == ARCHIVE_ITEM_BINARY || ptoc->typcd == ARCHIVE_ITEM_DATA ||
                ptoc->typcd == ARCHIVE_ITEM_ZIPFILE)
            return true;
        if (ptoc->typcd == ARCHIVE_ITEM_DEPENDENCY) {
            return true;
        }
		ptoc = pyi_arch_increment_toc_ptr(status_list[SELF], ptoc);
	}
	return false;
}

/*
 * extract all binaries (type 'b') and all data files (type 'x') to the filesystem
 * and checks for dependencies (type 'd'). If dependencies are found, extract them.
 */
int extractBinaries(ARCHIVE_STATUS *status_list[])
{
	TOC * ptoc = status_list[SELF]->tocbuff;
	VS("Extracting binaries\n");
	while (ptoc < status_list[SELF]->tocend) {
		if (ptoc->typcd == ARCHIVE_ITEM_BINARY || ptoc->typcd == ARCHIVE_ITEM_DATA ||
                ptoc->typcd == ARCHIVE_ITEM_ZIPFILE)
			if (pyi_arch_extract2fs(status_list[SELF], ptoc))
				return -1;

        if (ptoc->typcd == ARCHIVE_ITEM_DEPENDENCY) {
            if (extractDependency(status_list, ptoc->name) == -1)
                return -1;
        }
		ptoc = pyi_arch_increment_toc_ptr(status_list[SELF], ptoc);
	}
	return 0;
}

/*
 * Run scripts
 * Return non zero on failure
 */
int pyi_pylib_run_scripts(ARCHIVE_STATUS *status)
{
	unsigned char *data;
	char buf[PATH_MAX];
	int rc = 0;
	TOC * ptoc = status->tocbuff;
	PyObject *__main__ = PI_PyImport_AddModule("__main__");
	PyObject *__file__;
	VS("Running scripts\n");

	/* Iterate through toc looking for scripts (type 's') */
	while (ptoc < status->tocend) {
		if (ptoc->typcd == ARCHIVE_ITEM_PYSOURCE) {
			/* Get data out of the archive.  */
			data = pyi_arch_extract(status, ptoc);
			/* Set the __file__ attribute within the __main__ module,
			   for full compatibility with normal execution. */
			strcpy(buf, ptoc->name);
			strcat(buf, ".py");
            __file__ = PI_PyString_FromStringAndSize(buf, strlen(buf));
            PI_PyObject_SetAttrString(__main__, "__file__", __file__);
            Py_DECREF(__file__);
			/* Run it */
			rc = PI_PyRun_SimpleString((char *) data);
			/* log errors and abort */
			if (rc != 0) {
				VS("RC: %d from %s\n", rc, ptoc->name);
				return rc;
			}
			free(data);
		}

		ptoc = pyi_arch_increment_toc_ptr(status, ptoc);
	}
	return 0;
}

/*
 * call a simple "int func(void)" entry point.  Assumes such a function
 * exists in the main namespace.
 * Return non zero on failure, with -2 if the specific error is
 * that the function does not exist in the namespace.
 */
int callSimpleEntryPoint(char *name, int *presult)
{
	int rc = -1;
	/* Objects with no ref. */
	PyObject *mod, *dict;
	/* Objects with refs to kill. */
	PyObject *func = NULL, *pyresult = NULL;

	mod = PI_PyImport_AddModule("__main__"); /* NO ref added */
	if (!mod) {
		VS("No __main__\n");
		goto done;
	}
	dict = PI_PyModule_GetDict(mod); /* NO ref added */
	if (!mod) {
		VS("No __dict__\n");
		goto done;
	}
	func = PI_PyDict_GetItemString(dict, name);
	if (func == NULL) { /* should explicitly check KeyError */
		VS("CallSimpleEntryPoint can't find the function name\n");
		rc = -2;
		goto done;
	}
	pyresult = PI_PyObject_CallFunction(func, "");
	if (pyresult==NULL) goto done;
	PI_PyErr_Clear();
	*presult = PI_PyInt_AsLong(pyresult);
	rc = PI_PyErr_Occurred() ? -1 : 0;
	VS( rc ? "Finished with failure\n" : "Finished OK\n");
	/* all done! */
done:
	Py_XDECREF(func);
	Py_XDECREF(pyresult);
	/* can't leave Python error set, else it may
	   cause failures in later async code */
	if (rc)
		/* But we will print them 'cos they may be useful */
		PI_PyErr_Print();
	PI_PyErr_Clear();
	return rc;
}

/* for finer grained control */
/*
 * initialize (this always needs to be done)
 */
int init(ARCHIVE_STATUS *status, char const * archivePath, char  const * archiveName)
{
	/* Set up paths */
	if (pyi_arch_set_paths(status, archivePath, archiveName))
		return -1;

	/* Open the archive */
	if (pyi_arch_open(status))
		return -1;

	return 0;
}

/*
 * Once init'ed, you might want to extractBinaries()
 * If you do, what comes after is very platform specific.
 * Once you've taken care of the platform specific details,
 * or if there are no binaries to extract, you go on
 * to doIt(), which is the important part.
 */
int doIt(ARCHIVE_STATUS *status, int argc, char *argv[])
{
	int rc = 0;
	/* Load Python DLL */
	if (pyi_pylib_load(status))
		return -1;

	/* Start Python. */
	if (pyi_pylib_start_python(status, argc, argv))
		return -1;

	/* Import modules from archive - bootstrap */
	if (pyi_pylib_import_modules(status))
		return -1;

	/* Install zlibs  - now all hooks in place */
	if (pyi_pylib_install_zlibs(status))
		return -1;

	/* Run scripts */
	rc = pyi_pylib_run_scripts(status);

	VS("OK.\n");

	return rc;
}
