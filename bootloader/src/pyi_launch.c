/*
 * ****************************************************************************
 * Copyright (c) 2013-2023, PyInstaller Development Team.
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

#ifdef _WIN32
    #include <windows.h>
#else
    #include <stdlib.h>   /* malloc */
#endif
#include <string.h>   /* memset */
#include <stddef.h>   /* ptrdiff_t */

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
#include "pyi_multipkg.h"


/*
 * Extract all binaries (type 'b') and all data files (type 'x') to the filesystem
 * and checks for dependencies (type 'd'). If dependencies are found, extract them.
 *
 * 'Multipackage' feature includes dependencies. Dependencies are files in other
 * .exe files. Having files in other executables allows share binary files among
 * executables and thus reduce the final size of the executable.
 *
 * If 'splash screen' feature is enabled, the text on splash screen will be updated
 * during the extraction with the name of currently processed TOC entry.
 */
int
pyi_launch_extract_files_from_archive(PYI_CONTEXT *pyi_ctx)
{
    const TOC *toc_entry;
    ptrdiff_t index;
    int retcode = 0;

    ARCHIVE_STATUS *multipkg_archive_pool[PYI_MULTIPKG_ARCHIVE_POOL_SIZE];

    /* Clear the archive pool array. */
    memset(multipkg_archive_pool, 0, sizeof(multipkg_archive_pool));

    toc_entry = pyi_ctx->archive->tocbuff;
    while (toc_entry < pyi_ctx->archive->tocend) {
        if (toc_entry->typcd == ARCHIVE_ITEM_BINARY || toc_entry->typcd == ARCHIVE_ITEM_DATA ||
            toc_entry->typcd == ARCHIVE_ITEM_ZIPFILE || toc_entry->typcd == ARCHIVE_ITEM_SYMLINK) {
            /* 'Splash screen' feature */
            if (pyi_ctx->splash != NULL) {
                /* Update the text on the splash screen if one is available */
                pyi_splash_update_prg(pyi_ctx->splash, toc_entry);
            }

            /* Extract the file to the disk */
            if (pyi_arch_extract2fs(pyi_ctx->archive, toc_entry)) {
                retcode = -1;
                break;  /* No need to extract other items in case of error. */
            }
        }

        else {
            /* 'Multipackage' feature - dependency is stored in different executables. */
            if (toc_entry->typcd == ARCHIVE_ITEM_DEPENDENCY) {
                if (pyi_multipkg_extract_dependency(pyi_ctx, multipkg_archive_pool, toc_entry->name) == -1) {
                    retcode = -1;
                    break;  /* No need to extract other items in case of error. */
                }
            }
        }
        toc_entry = pyi_arch_increment_toc_ptr(pyi_ctx->archive, toc_entry);
    }

    /* Free memory allocated for archive pool. */
    for (index = 0; multipkg_archive_pool[index] != NULL; index++) {
        pyi_arch_status_free(multipkg_archive_pool[index]);
    }

    return retcode;
}


/* These helper functions are used only in windowed bootloader variants. */
#if defined(WINDOWED)

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

#endif /* if defined(WINDOWED) */

/*
 * Run scripts
 * Return non zero on failure
 */
int
pyi_launch_run_scripts(const ARCHIVE_STATUS *status)
{
    unsigned char *data;
    char buf[PATH_MAX];
    const TOC *ptoc = status->tocbuff;
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
             * attribute, so it can be retrieved by PyiFrozenImporter,
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
    } else {
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

    /* Install PYZ archive */
    if (pyi_pylib_install_pyz(status)) {
        return -1;
    }

    /* Run scripts */
    rc = pyi_launch_run_scripts(status);

    if (rc == 0) {
        VS("LOADER: OK.\n");
    } else {
        VS("LOADER: ERROR.\n");
    }

    return rc;
}

void
pyi_launch_finalize(ARCHIVE_STATUS *status)
{
    pyi_pylib_finalize(status);
}
