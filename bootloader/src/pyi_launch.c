/*
 * ****************************************************************************
 * Copyright (c) 2013-2021, PyInstaller Development Team.
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
 * Launch a python module from an archive.
 */

#if defined(__APPLE__) && defined(WINDOWED)
    #include <Carbon/Carbon.h>  /* TransformProcessType */
#endif

#ifdef _WIN32
    #include <windows.h>
#else
    #include <langinfo.h> /* CODESET, nl_langinfo */
    #include <stdlib.h>   /* malloc */
#endif
#include <locale.h>  /* setlocale */
#include <stdarg.h>
#include <stddef.h>   /* ptrdiff_t */
#include <stdio.h>    /* vsnprintf */
#include <string.h>   /* strcpy */
#include <sys/stat.h> /* struct stat */

/* PyInstaller headers. */
#include "pyi_launch.h"
#include "pyi_global.h"
#include "pyi_path.h"
#include "pyi_archive.h"
#include "pyi_utils.h"
#include "pyi_splash.h"
#include "pyi_python.h"
#include "pyi_pythonlib.h"
#include "pyi_win32_utils.h"  /* CreateActContext */
#include "pyi_exception_dialog.h"

/* Max count of possible opened archives in multipackage mode. */
#define _MAX_ARCHIVE_POOL_LEN 20

/*
 * The functions in this file defined in reverse order so that forward
 * declarations are not necessary.
 */

int
checkFile(char *buf, const char *fmt, ...)
{
    va_list args;
    struct stat tmp;

    va_start(args, fmt);
    if (vsnprintf(buf, PATH_MAX, fmt, args) >= PATH_MAX) {
        return -1;
    };
    va_end(args);

    return stat(buf, &tmp);
}

/* Splits the item in the form path:filename */
int
splitName(char *path, char *filename, const char *item)
{
    char *p;

    VS("LOADER: Splitting item into path and filename\n");
    // copy directly into destination buffer and manipulate there
    if (snprintf(path, PATH_MAX, "%s", item) >= PATH_MAX) {
        return -1;
    }
    p = strchr(path, ':');
    if (p == NULL) { // No colon in string
        return -1;
    };
    p[0] ='\0'; // terminate path part
    // `path` fits into PATH_MAX, so will all substrings
    strcpy(filename, ++p);
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

    archive = pyi_arch_status_new();
    if (archive == NULL) {
        return NULL;
    }

    if ((snprintf(archive->archivename, PATH_MAX, "%s", path) >= PATH_MAX) ||
        (snprintf(archive->homepath, PATH_MAX, "%s",
                  archive_pool[SELF]->homepath) >= PATH_MAX) ||
        (snprintf(archive->temppath, PATH_MAX, "%s",
                  archive_pool[SELF]->temppath) >= PATH_MAX)) {
        FATALERROR("Archive path exceeds PATH_MAX\n");
        pyi_arch_status_free(archive);
        return NULL;
    }

    /*
     * Setting this flag prevents creating another temp directory and
     * the directory from the main archive status is used.
     */
    archive->has_temp_directory = archive_pool[SELF]->has_temp_directory;

    if (pyi_arch_open(archive)) {
        FATAL_PERROR("malloc", "Error opening archive %s\n", path);
        pyi_arch_status_free(archive);
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
            FATALERROR("Error copying %s\n", filename);
            return -1;
        }
        /* TODO implement pyi_path_join to accept variable length of arguments for this case. */
    }
    else if (checkFile(srcpath, "%s%s%s%s%s%s%s", archive_status->homepath, PYI_SEPSTR,
                       "..", PYI_SEPSTR, dirname, PYI_SEPSTR, filename) == 0) {
        VS("LOADER: File %s found, assuming is onedir\n", srcpath);

        if (copyDependencyFromDir(archive_status, srcpath, filename) == -1) {
            FATALERROR("Error copying %s\n", filename);
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
            pyi_arch_status_free(status);
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
 *
 * 'Splash screen' feature is supported by passing a SPLASH_STATUS to this
 * function. The parameter may be NULL, if not the name of the TOC is displayed
 * on the splash screen asynchronously.
 */
int
pyi_launch_extract_binaries(ARCHIVE_STATUS *archive_status, SPLASH_STATUS *splash_status)
{
    int retcode = 0;
    ptrdiff_t index = 0;
    /* We create this cache variable for faster execution time */
    bool update_text = (splash_status != NULL);

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
            /* 'Splash screen' feature */
            if (update_text) {
                /* Update the text on the splash screen if one is available */
                pyi_splash_update_prg(splash_status, ptoc);
            }

            /* Extract the file to the disk */
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
        pyi_arch_status_free(archive_pool[index]);
    }

    return retcode;
}

/*
 * Extract python exception message (string representation) from pvalue
 * part of the error indicator data returned by PyErr_Fetch().
 * Returns a copy of message string or NULL. Must be freed by caller.
 */
static char *
_pyi_extract_exception_message(PyObject *pvalue)
{
    PyObject *pvalue_str;
    const char *pvalue_cchar;
    char *retval = NULL;

    pvalue_str = PI_PyObject_Str(pvalue);
    pvalue_cchar = PI_PyUnicode_AsUTF8(pvalue_str);
    if (pvalue_cchar) {
        retval = strdup(pvalue_cchar);
    }
    PI_Py_DecRef(pvalue_str);

    return retval;
}

/*
 * Traceback formatting options for _pyi_extract_exception_traceback.
 */
enum
{
    /* String representation of the list containing traceback lines. */
    PYI_TB_FMT_REPR = 0,
    /* Concatenate the traceback lines into single string, using
     * default LF newlines. */
    PYI_TB_FMT_LF = 1,
    /* Concatenate the traceback lines into single string, and replace
     * the LF newlines with CRLF. */
    PYI_TB_FMT_CRLF = 2
};

/*
 * Extract python exception traceback from error indicator data
 * returned by PyErr_Fetch().
 * Returns a copy of traceback string or NULL. Must be freed by caller.
 */
static char *
_pyi_extract_exception_traceback(PyObject *ptype, PyObject *pvalue,
                                 PyObject *ptraceback, int fmt_mode)
{
    PyObject *module;
    char *retval = NULL;

    /* Attempt to get a full traceback, source lines will only
     * be available with --noarchive option */
    module = PI_PyImport_ImportModule("traceback");
    if (module != NULL) {
        PyObject *func = PI_PyObject_GetAttrString(module, "format_exception");
        if (func) {
            PyObject *tb = NULL;
            PyObject *tb_str = NULL;
            const char *tb_cchar = NULL;
            tb = PI_PyObject_CallFunctionObjArgs(func, ptype, pvalue,
                                                 ptraceback, NULL);
            if (tb != NULL) {
                if (fmt_mode == PYI_TB_FMT_REPR) {
                    /* Represent the list as string */
                    tb_str = PI_PyObject_Str(tb);
                } else {
                    /* Join the list using empty string */
                    PyObject *tb_empty = PI_PyUnicode_FromString("");
                    tb_str = PI_PyUnicode_Join(tb_empty, tb);
                    PI_Py_DecRef(tb_empty);
                    if (fmt_mode == PYI_TB_FMT_CRLF) {
                        /* Replace LF with CRLF */
                        PyObject *lf = PI_PyUnicode_FromString("\n");
                        PyObject *crlf = PI_PyUnicode_FromString("\r\n");
                        PyObject *tb_str_crlf = PI_PyUnicode_Replace(tb_str, lf, crlf, -1);
                        PI_Py_DecRef(lf);
                        PI_Py_DecRef(crlf);
                        /* Swap */
                        PI_Py_DecRef(tb_str);
                        tb_str = tb_str_crlf;
                    }
                }
            }
            if (tb_str != NULL) {
                tb_cchar = PI_PyUnicode_AsUTF8(tb_str);
                if (tb_cchar) {
                    retval = strdup(tb_cchar);
                }
            }
            PI_Py_DecRef(tb);
            PI_Py_DecRef(tb_str);
        }
        PI_Py_DecRef(func);
    }
    PI_Py_DecRef(module);

    return retval;
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
        FATALERROR("Could not get __main__ module.\n");
        return -1;
    }

    main_dict = PI_PyModule_GetDict(__main__);

    if (!main_dict) {
        FATALERROR("Could not get __main__ module's dict.\n");
        return -1;
    }

    /* Iterate through toc looking for scripts (type 's') */
    while (ptoc < status->tocend) {
        if (ptoc->typcd == ARCHIVE_ITEM_PYSOURCE) {
            /* Get data out of the archive.  */
            data = pyi_arch_extract(status, ptoc);
            /* Set the __file__ attribute within the __main__ module,
             *  for full compatibility with normal execution. */
            if (snprintf(buf, PATH_MAX, "%s%c%s.py", status->mainpath, PYI_SEP, ptoc->name) >= PATH_MAX) {
                FATALERROR("Absolute path to script exceeds PATH_MAX\n");
                return -1;
            }
            VS("LOADER: Running %s.py\n", ptoc->name);
            __file__ = PI_PyUnicode_FromString(buf);
            PI_PyObject_SetAttrString(__main__, "__file__", __file__);
            PI_Py_DecRef(__file__);

            /* Unmarshall code object */
            code = PI_PyMarshal_ReadObjectFromString((const char *) data, ptoc->ulen);
            if (!code) {
                FATALERROR("Failed to unmarshal code object for %s\n", ptoc->name);
                PI_PyErr_Print();
                return -1;
            }

            /* Store the code object to __main__ module's _pyi_main_co
             * attribute, so it can be retrieved by FrozenImporter,
             * if necessary. */
            PI_PyObject_SetAttrString(__main__, "_pyi_main_co", code);

            /* Run it */
            retval = PI_PyEval_EvalCode(code, main_dict, main_dict);

            /* If retval is NULL, an error occurred. Otherwise, it is a Python object.
             * (Since we evaluate module-level code, which is not allowed to return an
             * object, the Python object returned is always None.) */
            if (!retval) {
                #if defined(WINDOWED)
                    /* In windowed mode, we need to display error information
                     * via non-console means (i.e., error dialog on Windows,
                     * syslog on macOS). For that, we need to extract the error
                     * indicator data before PyErr_Print() call below clears
                     * it. But it seems that for PyErr_Print() to properly
                     * exit on SystemExit(), we also need to restore the error
                     * indicator via PyErr_Restore(). Therefore, we extract
                     * deep copies of relevant strings, and release all
                     * references to error indicator and its data.
                     */
                    PyObject *ptype, *pvalue, *ptraceback;
                    char *msg_exc, *msg_tb;
                    int fmt_mode = PYI_TB_FMT_REPR;

                    #if defined(_WIN32)
                        fmt_mode = PYI_TB_FMT_CRLF;
                    #elif defined(__APPLE__)
                        fmt_mode = PYI_TB_FMT_LF;
                    #endif

                    PI_PyErr_Fetch(&ptype, &pvalue, &ptraceback);
                    PI_PyErr_NormalizeException(&ptype, &pvalue, &ptraceback);
                    msg_exc = _pyi_extract_exception_message(pvalue);
                    if (pyi_arch_get_option(status, "pyi-disable-windowed-traceback") != NULL) {
                        /* Traceback is disabled via option */
                        msg_tb = strdup("Traceback is disabled via bootloader option.");
                    } else {
                        msg_tb = _pyi_extract_exception_traceback(
                            ptype, pvalue, ptraceback, fmt_mode);
                    }
                    PI_PyErr_Restore(ptype, pvalue, ptraceback);
                #endif

                /* If the error was SystemExit, PyErr_Print calls exit() without
                 * returning. This means we won't print "Failed to execute" on
                 * normal SystemExit's.
                 */
                PI_PyErr_Print();

                /* Display error information */
                #if !defined(WINDOWED)
                    /* Non-windowed mode; PyErr_print() above dumps the
                     * traceback, so the only thing we need to do here
                     * is provide a summary */
                     FATALERROR("Failed to execute script '%s' due to unhandled exception!\n", ptoc->name);
                #else
                    #if defined(_WIN32)
                        /* Windows; use custom dialog */
                        pyi_unhandled_exception_dialog(ptoc->name, msg_exc, msg_tb);
                    #elif defined(__APPLE__)
                        /* macOS .app bundle; use FATALERROR(), which
                         * prints to stderr (invisible) as well as sends
                         * the message to syslog */
                         FATALERROR("Failed to execute script '%s' due to unhandled exception: %s\n", ptoc->name, msg_exc);
                         FATALERROR("Traceback:\n%s\n", msg_tb);
                    #endif

                    /* Clean up exception information strings */
                    free(msg_exc);
                    free(msg_tb);
                #endif /* if !defined(WINDOWED) */

                /* Be consistent with python interpreter, which returns
                 * 1 if it exits due to unhandled exception.
                 */
                return 1;
            }
            free(data);
        }

        ptoc = pyi_arch_increment_toc_ptr(status, ptoc);
    }
    return 0;
}

void
pyi_launch_initialize(ARCHIVE_STATUS * status)
{
    /* Nothing to do here at the moment. */
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
