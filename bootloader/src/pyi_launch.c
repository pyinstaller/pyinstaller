/*
 * ****************************************************************************
 * Copyright (c) 2013-2016, PyInstaller Development Team.
 * Distributed under the terms of the GNU General Public License with exception
 * for distributing bootloader.
 *
 * The full license is in the file COPYING.txt, distributed with this software.
 * ****************************************************************************
 */

/*
 * Launch a python module from an archive.
 */

/* TODO: use safe string functions */
#define _CRT_SECURE_NO_WARNINGS 1

#if defined(__APPLE__) && defined(WINDOWED)
    #include <Carbon/Carbon.h>  /* TransformProcessType */
#endif

#ifdef _WIN32
    #include <windows.h>
    #include <winsock.h>  /* ntohl */
#else
    #ifdef __FreeBSD__
/* freebsd issue #188316 */
        #include <arpa/inet.h>  /* ntohl */
    #else
        #include <netinet/in.h>  /* ntohl */
    #endif
    #include <langinfo.h> /* CODESET, nl_langinfo */
    #include <limits.h>   /* PATH_MAX */
    #include <stdlib.h>   /* malloc */
#endif
#include <locale.h>  /* setlocale */
#include <stdarg.h>
#include <stddef.h>   /* ptrdiff_t */
#include <stdio.h>    /* vsnprintf */
#include <string.h>   /* strcpy */
#include <sys/stat.h> /* struct stat */

/* PyInstaller headers. */
#include "pyi_global.h"
#include "pyi_path.h"
#include "pyi_archive.h"
#include "pyi_utils.h"
#include "pyi_python.h"
#include "pyi_pythonlib.h"
#include "pyi_win32_utils.h"  /* CreateActContext */

/* Max count of possible opened archives in multipackage mode. */
#define _MAX_ARCHIVE_POOL_LEN 20

/*
 * The functions in this file defined in reverse order so that forward
 * declarations are not necessary.
 */

static int
checkFile(char *buf, const char *fmt, ...)
{
    va_list args;
    struct stat tmp;

    va_start(args, fmt);
    vsnprintf(buf, PATH_MAX, fmt, args);
    va_end(args);

    return stat(buf, &tmp);
}

/* Splits the item in the form path:filename */
static int
splitName(char *path, char *filename, const char *item)
{
    char name[PATH_MAX + 1];

    VS("LOADER: Splitting item into path and filename\n");
    strcpy(name, item);
    strcpy(path, strtok(name, ":"));
    strcpy(filename, strtok(NULL, ":"));

    if (path[0] == 0 || filename[0] == 0) {
        return -1;
    }
    return 0;
}

/* Copy the dependencies file from a directory to the tempdir */
static int
copyDependencyFromDir(ARCHIVE_STATUS *status, const char *srcpath, const char *filename)
{
    if (pyi_create_temp_path(status) == -1) {
        return -1;
    }

    VS("LOADER: Coping file %s to %s\n", srcpath, status->temppath);

    if (pyi_copy_file(srcpath, status->temppath, filename) == -1) {
        return -1;
    }
    return 0;
}

/*
 * Look for the archive identified by path into the ARCHIVE_STATUS pool archive_pool.
 * If the archive is found, a pointer to the associated ARCHIVE_STATUS is returned
 * otherwise the needed archive is opened and added to the pool and then returned.
 * If an error occurs, returns NULL.
 *
 * Having several archives is useful for sharing binary dependencies with several
 * executables (multipackage feature).
 */
static ARCHIVE_STATUS *
_get_archive(ARCHIVE_STATUS *archive_pool[], const char *path)
{
    ARCHIVE_STATUS *archive = NULL;
    int index = 0;
    int SELF = 0;

    VS("LOADER: Getting file from archive.\n");

    if (pyi_create_temp_path(archive_pool[SELF]) == -1) {
        return NULL;
    }

    for (index = 1; archive_pool[index] != NULL; index++) {
        if (strcmp(archive_pool[index]->archivename, path) == 0) {
            VS("LOADER: Archive found: %s\n", path);
            return archive_pool[index];
        }
        VS("LOADER: Checking next archive in the list...\n");
    }

    archive = (ARCHIVE_STATUS *) malloc(sizeof(ARCHIVE_STATUS));

    if (archive == NULL) {
        FATALERROR("Error allocating memory for status\n");
        return NULL;
    }

    strcpy(archive->archivename, path);
    strcpy(archive->homepath, archive_pool[SELF]->homepath);
    strcpy(archive->temppath, archive_pool[SELF]->temppath);
    /*
     * Setting this flag prevents creating another temp directory and
     * the directory from the main archive status is used.
     */
    archive->has_temp_directory = archive_pool[SELF]->has_temp_directory;

    if (pyi_arch_open(archive)) {
        FATALERROR("Error openning archive %s\n", path);
        free(archive);
        return NULL;
    }

    archive_pool[index] = archive;
    return archive;
}

/* Extract a file identifed by filename from the archive associated to status. */
static int
extractDependencyFromArchive(ARCHIVE_STATUS *status, const char *filename)
{
    TOC * ptoc = status->tocbuff;

    VS("LOADER: Extracting dependencies from archive\n");

    while (ptoc < status->tocend) {
        if (strcmp(ptoc->name, filename) == 0) {
            if (pyi_arch_extract2fs(status, ptoc)) {
                return -1;
            }
        }
        ptoc = pyi_arch_increment_toc_ptr(status, ptoc);
    }
    return 0;
}

/* Decide if the dependency identified by item is in a onedir or onfile archive
 * then call the appropriate function.
 */
static int
_extract_dependency(ARCHIVE_STATUS *archive_pool[], const char *item)
{
    ARCHIVE_STATUS *status = NULL;
    ARCHIVE_STATUS *archive_status = archive_pool[0];
    char path[PATH_MAX];
    char filename[PATH_MAX];
    char srcpath[PATH_MAX];
    char archive_path[PATH_MAX];

    char dirname[PATH_MAX];

    VS("LOADER: Extracting dependencies\n");

    if (splitName(path, filename, item) == -1) {
        return -1;
    }

    pyi_path_dirname(dirname, path);

    /* We need to identify three situations: 1) dependecies are in a onedir archive
     * next to the current onefile archive, 2) dependencies are in a onedir/onefile
     * archive next to the current onedir archive, 3) dependencies are in a onefile
     * archive next to the current onefile archive.
     */
    VS("LOADER: Checking if file exists\n");

    /* TODO implement pyi_path_join to accept variable length of arguments for this case. */
    if (checkFile(srcpath, "%s%s%s%s%s", archive_status->homepath, PYI_SEPSTR, dirname,
                  PYI_SEPSTR, filename) == 0) {
        VS("LOADER: File %s found, assuming is onedir\n", srcpath);

        if (copyDependencyFromDir(archive_status, srcpath, filename) == -1) {
            FATALERROR("Error coping %s\n", filename);
            return -1;
        }
        /* TODO implement pyi_path_join to accept variable length of arguments for this case. */
    }
    else if (checkFile(srcpath, "%s%s%s%s%s%s%s", archive_status->homepath, PYI_SEPSTR,
                       "..", PYI_SEPSTR, dirname, PYI_SEPSTR, filename) == 0) {
        VS("LOADER: File %s found, assuming is onedir\n", srcpath);

        if (copyDependencyFromDir(archive_status, srcpath, filename) == -1) {
            FATALERROR("Error coping %s\n", filename);
            return -1;
        }
    }
    else {
        VS("LOADER: File %s not found, assuming is onefile.\n", srcpath);

        /* TODO implement pyi_path_join to accept variable length of arguments for this case. */
        if ((checkFile(archive_path, "%s%s%s.pkg", archive_status->homepath, PYI_SEPSTR,
                       path) != 0) &&
            (checkFile(archive_path, "%s%s%s.exe", archive_status->homepath, PYI_SEPSTR,
                       path) != 0) &&
            (checkFile(archive_path, "%s%s%s", archive_status->homepath, PYI_SEPSTR,
                       path) != 0)) {
            FATALERROR("Archive not found: %s\n", archive_path);
            return -1;
        }

        if ((status = _get_archive(archive_pool, archive_path)) == NULL) {
            FATALERROR("Archive not found: %s\n", archive_path);
            return -1;
        }

        if (extractDependencyFromArchive(status, filename) == -1) {
            FATALERROR("Error extracting %s\n", filename);
            free(status);
            return -1;
        }
    }

    return 0;
}

/*
 * Check if binaries need to be extracted. If not, this is probably a onedir solution,
 * and a child process will not be required on windows.
 */
int
pyi_launch_need_to_extract_binaries(ARCHIVE_STATUS *archive_status)
{
    TOC * ptoc = archive_status->tocbuff;

    while (ptoc < archive_status->tocend) {
        if (ptoc->typcd == ARCHIVE_ITEM_BINARY || ptoc->typcd == ARCHIVE_ITEM_DATA ||
            ptoc->typcd == ARCHIVE_ITEM_ZIPFILE) {
            return true;
        }

        if (ptoc->typcd == ARCHIVE_ITEM_DEPENDENCY) {
            return true;
        }
        ptoc = pyi_arch_increment_toc_ptr(archive_status, ptoc);
    }
    return false;
}

/*
 * Extract all binaries (type 'b') and all data files (type 'x') to the filesystem
 * and checks for dependencies (type 'd'). If dependencies are found, extract them.
 *
 * 'Multipackage' feature includes dependencies. Dependencies are files in other
 * .exe files. Having files in other executables allows share binary files among
 * executables and thus reduce the final size of the executable.
 */
int
pyi_launch_extract_binaries(ARCHIVE_STATUS *archive_status)
{
    int retcode = 0;
    ptrdiff_t index = 0;

    /*
     * archive_pool[0] is reserved for the main process, the others for dependencies.
     */
    ARCHIVE_STATUS *archive_pool[_MAX_ARCHIVE_POOL_LEN];
    TOC * ptoc = archive_status->tocbuff;

    /* Clean memory for archive_pool list. */
    memset(&archive_pool, 0, _MAX_ARCHIVE_POOL_LEN * sizeof(ARCHIVE_STATUS *));

    /* Current process is the 1st item. */
    archive_pool[0] = archive_status;

    VS("LOADER: Extracting binaries\n");

    while (ptoc < archive_status->tocend) {
        if (ptoc->typcd == ARCHIVE_ITEM_BINARY || ptoc->typcd == ARCHIVE_ITEM_DATA ||
            ptoc->typcd == ARCHIVE_ITEM_ZIPFILE) {
            if (pyi_arch_extract2fs(archive_status, ptoc)) {
                retcode = -1;
                break;  /* No need to extract other items in case of error. */
            }
        }

        else {
            /* 'Multipackage' feature - dependency is stored in different executables. */
            if (ptoc->typcd == ARCHIVE_ITEM_DEPENDENCY) {
                if (_extract_dependency(archive_pool, ptoc->name) == -1) {
                    retcode = -1;
                    break;  /* No need to extract other items in case of error. */
                }

            }
        }
        ptoc = pyi_arch_increment_toc_ptr(archive_status, ptoc);
    }

    /*
     * Free memory allocated for archive_pool data. Do not free memory
     * of the main process - start with 2nd item.
     */
    for (index = 1; archive_pool[index] != NULL; index++) {
        pyi_arch_status_free_memory(archive_pool[index]);
    }

    return retcode;
}

/*
 * Run scripts
 * Return non zero on failure
 */
int
pyi_launch_run_scripts(ARCHIVE_STATUS *status)
{
    unsigned char *data;
    char buf[PATH_MAX];
    TOC * ptoc = status->tocbuff;
    PyObject *__main__;
    PyObject *__file__;
    PyObject *main_dict;
    PyObject *code, *retval;

    __main__ = PI_PyImport_AddModule("__main__");

    if (!__main__) {
        FATALERROR("Could not get __main__ module.");
        return -1;
    }

    main_dict = PI_PyModule_GetDict(__main__);

    if (!main_dict) {
        FATALERROR("Could not get __main__ module's dict.");
        return -1;
    }

    /* Iterate through toc looking for scripts (type 's') */
    while (ptoc < status->tocend) {
        if (ptoc->typcd == ARCHIVE_ITEM_PYSOURCE) {
            /* Get data out of the archive.  */
            data = pyi_arch_extract(status, ptoc);
            /* Set the __file__ attribute within the __main__ module,
             *  for full compatibility with normal execution. */
            strcpy(buf, ptoc->name);
            strcat(buf, ".py");
            VS("LOADER: Running %s\n", buf);

            if (is_py2) {
                __file__ = PI_PyString_FromString(buf);
            }
            else {
                __file__ = PI_PyUnicode_FromString(buf);
            };
            PI_PyObject_SetAttrString(__main__, "__file__", __file__);
            Py_DECREF(__file__);

            /* Unmarshall code object */
            code = PI_PyMarshal_ReadObjectFromString((const char *) data, ntohl(ptoc->ulen));

            if (!code) {
                FATALERROR("Failed to unmarshal code object for %s\n", ptoc->name);
                PI_PyErr_Print();
                return -1;
            }
            /* Run it */
            retval = PI_PyEval_EvalCode(code, main_dict, main_dict);

            /* If retval is NULL, an error occured. Otherwise, it is a Python object.
             * (Since we evaluate module-level code, which is not allowed to return an
             * object, the Python object returned is always None.) */
            if (!retval) {
                PI_PyErr_Print();
                /* If the error was SystemExit, PyErr_Print calls exit() without
                 * returning. So don't print "Failed to execute" on SystemExit. */
                FATALERROR("Failed to execute script %s\n", ptoc->name);
                return -1;
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
int
callSimpleEntryPoint(char *name, int *presult)
{
    int rc = -1;
    /* Objects with no ref. */
    PyObject *mod, *dict;
    /* Objects with refs to kill. */
    PyObject *func = NULL, *pyresult = NULL;

    mod = PI_PyImport_AddModule("__main__");  /* NO ref added */

    if (!mod) {
        VS("LOADER: No __main__\n");
        goto done;
    }
    dict = PI_PyModule_GetDict(mod);  /* NO ref added */

    if (!mod) {
        VS("LOADER: No __dict__\n");
        goto done;
    }
    func = PI_PyDict_GetItemString(dict, name);

    if (func == NULL) {  /* should explicitly check KeyError */
        VS("LOADER: CallSimpleEntryPoint can't find the function name\n");
        rc = -2;
        goto done;
    }
    pyresult = PI_PyObject_CallFunction(func, "");

    if (pyresult == NULL) {
        goto done;
    }
    PI_PyErr_Clear();
    *presult = PI_PyLong_AsLong(pyresult);
    rc = PI_PyErr_Occurred() ? -1 : 0;
    VS( rc ? "LOADER: Finished with failure\n" : "LOADER: Finished OK\n");
    /* all done! */
done:
    Py_XDECREF(func);
    Py_XDECREF(pyresult);

    /* can't leave Python error set, else it may
     *  cause failures in later async code */
    if (rc) {
        /* But we will print them 'cos they may be useful */
        PI_PyErr_Print();
    }
    PI_PyErr_Clear();
    return rc;
}

/* For finer grained control. */

void
pyi_launch_initialize(ARCHIVE_STATUS * status)
{
#if defined(__APPLE__) && defined(WINDOWED)
    /*
     * On OS X this ensures that the application is handled as GUI app.
     * Call TransformProcessType() in the child process.
     */
    ProcessSerialNumber psn = { 0, kCurrentProcess };
    OSStatus returnCode = TransformProcessType(&psn,
                                               kProcessTransformToForegroundApplication);
#elif defined(_WIN32)
    char * manifest;
    manifest = pyi_arch_get_option(status, "pyi-windows-manifest-filename");

    if (NULL != manifest) {
        manifest = pyi_path_join(NULL, status->mainpath, manifest);
        CreateActContext(manifest);
        free(manifest);
    }
#endif /* if defined(__APPLE__) && defined(WINDOWED) */
}

/*
 * Once init'ed, you might want to extractBinaries()
 * If you do, what comes after is very platform specific.
 * Once you've taken care of the platform specific details,
 * or if there are no binaries to extract, you go on
 * to pyi_launch_execute(), which is the important part.
 */
int
pyi_launch_execute(ARCHIVE_STATUS *status)
{
    int rc = 0;

    /* Load Python DLL */
    if (pyi_pylib_load(status)) {
        return -1;
    }
    else {
        /* With this flag Python cleanup will be called. */
        status->is_pylib_loaded = true;
    }

    /* Start Python. */
    if (pyi_pylib_start_python(status)) {
        return -1;
    }

    /* Import core pyinstaller modules from the executable - bootstrap */
    if (pyi_pylib_import_modules(status)) {
        return -1;
    }

    /* Install zlibs  - now all hooks in place */
    if (pyi_pylib_install_zlibs(status)) {
        return -1;
    }

#ifndef WIN32

    /*
     * On Linux sys.getfilesystemencoding() returns None but should not.
     * If it's None(NULL), get the filesystem encoding by using direct
     * C calls and override it with correct value.
     *
     * TODO: This may not be needed any more. Please confirm on Linux.
     */
    if (!*PI_Py_FileSystemDefaultEncoding) {
        char *saved_locale, *loc_codeset;
        saved_locale = strdup(setlocale(LC_CTYPE, NULL));
        VS("LOADER: LC_CTYPE was %s but resulted in NULL FileSystemDefaultEncoding\n",
           saved_locale);
        setlocale(LC_CTYPE, "");
        loc_codeset = nl_langinfo(CODESET);
        setlocale(LC_CTYPE, saved_locale);
        free(saved_locale);
        VS("LOADER: Setting FileSystemDefaultEncoding to %s (was NULL)\n", loc_codeset);
        *PI_Py_FileSystemDefaultEncoding = loc_codeset;
    }
#endif     /* WIN32 */

    /* Run scripts */
    rc = pyi_launch_run_scripts(status);

    VS("LOADER: OK.\n");

    return rc;
}

void
pyi_launch_finalize(ARCHIVE_STATUS *status)
{
    pyi_pylib_finalize(status);
}

/*
 * On OS X this ensures that the parent process goes to background.
 * Call TransformProcessType() in the parent process.
 */
void
pyi_parent_to_background()
{
#if defined(__APPLE__) && defined(WINDOWED)
    ProcessSerialNumber psn = { 0, kCurrentProcess };
    OSStatus returnCode = TransformProcessType(&psn,
                                               kProcessTransformToBackgroundApplication);
#endif
}
