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
#include "pyi_main.h"
#include "pyi_utils.h"
#include "pyi_splash.h"
#include "pyi_dylib_python.h"
#include "pyi_python.h"
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
pyi_launch_extract_files_from_archive(struct PYI_CONTEXT *pyi_ctx)
{
    const struct ARCHIVE *archive = pyi_ctx->archive;
    const struct TOC_ENTRY *toc_entry;
    ptrdiff_t index;
    int retcode = 0;
    char output_filename[PYI_PATH_MAX];

    struct ARCHIVE *multipkg_archive_pool[PYI_MULTIPKG_ARCHIVE_POOL_SIZE];
    char multipkg_ref[PYI_PATH_MAX];
    char multipkg_name[PYI_PATH_MAX];

    const char *entry_filename;

    /* Clear the archive pool array. */
    memset(multipkg_archive_pool, 0, sizeof(multipkg_archive_pool));

    for (toc_entry = archive->toc; toc_entry < archive->toc_end; toc_entry = pyi_archive_next_toc_entry(archive, toc_entry)) {
        /* Check if entry is extractable */
        switch (toc_entry->typecode) {
            /* Onefile mode */
            case ARCHIVE_ITEM_BINARY:
            case ARCHIVE_ITEM_DATA:
            case ARCHIVE_ITEM_ZIPFILE:
            case ARCHIVE_ITEM_SYMLINK: {
                /* toc_entry->name is the output filename */
                entry_filename = toc_entry->name;
                break;
            }
            /* MERGE multi-package */
            case ARCHIVE_ITEM_DEPENDENCY: {
                /* toc_entry->name is multi-package reference; split it */
                if (pyi_multipkg_split_dependency_string(multipkg_ref, multipkg_name, toc_entry->name) == -1) {
                    retcode = -1;
                }
                entry_filename = multipkg_name;
                break;
            }
            /* Not extractable; skip */
            default: {
                continue;
            }
        }

        /* Break on errors in the above switch */
        if (retcode != 0) {
            break;
        }

        /* Update splash screen (display name of the currently-processed entry) */
        if (pyi_ctx->splash != NULL) {
            pyi_splash_update_text(pyi_ctx->splash, entry_filename);
        }

        /* Construct output filename */
        if (snprintf(output_filename, PYI_PATH_MAX, "%s%c%s", pyi_ctx->application_home_dir, PYI_SEP, entry_filename) >= PYI_PATH_MAX) {
            PYI_ERROR("Extraction path length exceeds maximum path length!\n");
            retcode = -1;
            break;
        }

        /* Check if file already exists (it should not) */
        if (pyi_path_exists(output_filename) == 1) {
            /* Check if file was a splash screen requirement */
            if (pyi_ctx->splash && pyi_splash_is_splash_requirement(pyi_ctx->splash, entry_filename) == 1) {
                /* This is splash requirement, so it is expected to exist.
                 * Also, the file should be in use right now, so avoid
                 * overwriting it. */
                continue;
            } else if (pyi_ctx->strict_unpack_mode) {
                PYI_ERROR("File already exists but should not: %s\n", output_filename);
                retcode = -1;
                break;
            } else {
                PYI_WARNING("File already exists but should not: %s\n", output_filename);
            }
        }

        /* Create parent directory tree */
        if (pyi_create_parent_directory_tree(pyi_ctx, pyi_ctx->application_home_dir, entry_filename) < 0) {
            PYI_ERROR("Failed to create parent directory structure.\n");
            retcode = -1;
            break;
        }

        /* Extract */
        if (toc_entry->typecode == ARCHIVE_ITEM_DEPENDENCY) {
            retcode = pyi_multipkg_extract_dependency(
                pyi_ctx,
                multipkg_archive_pool,
                multipkg_ref,
                multipkg_name,
                output_filename
            );
        } else {
            retcode = pyi_archive_extract2fs(archive, toc_entry, output_filename);
        }

        /* If extraction failed, there is no need to continue. */
        if (retcode != 0) {
            PYI_ERROR("Failed to extract entry: %s.\n", toc_entry->name);
            break;
        }
    }

    /* Free memory allocated for archive pool. */
    for (index = 0; multipkg_archive_pool[index] != NULL; index++) {
        pyi_archive_free(&multipkg_archive_pool[index]);
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
_pyi_extract_exception_message(PyObject *pvalue, const struct DYLIB_PYTHON *dylib_python)
{
    PyObject *pvalue_str;
    const char *pvalue_cchar;
    char *retval = NULL;

    pvalue_str = dylib_python->PyObject_Str(pvalue);
    pvalue_cchar = dylib_python->PyUnicode_AsUTF8(pvalue_str);
    if (pvalue_cchar) {
        retval = strdup(pvalue_cchar);
    }
    dylib_python->Py_DecRef(pvalue_str);

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
_pyi_extract_exception_traceback(
    PyObject *ptype,
    PyObject *pvalue,
    PyObject *ptraceback,
    int fmt_mode,
    const struct DYLIB_PYTHON *dylib_python
)
{
    PyObject *module;
    char *retval = NULL;

    /* Attempt to get a full traceback, source lines will only
     * be available with --noarchive option */
    module = dylib_python->PyImport_ImportModule("traceback");
    if (module != NULL) {
        PyObject *func = dylib_python->PyObject_GetAttrString(module, "format_exception");
        if (func) {
            PyObject *tb = NULL;
            PyObject *tb_str = NULL;
            const char *tb_cchar = NULL;

            tb = dylib_python->PyObject_CallFunctionObjArgs(func, ptype, pvalue, ptraceback, NULL);
            if (tb != NULL) {
                if (fmt_mode == PYI_TB_FMT_REPR) {
                    /* Represent the list as string */
                    tb_str = dylib_python->PyObject_Str(tb);
                } else {
                    /* Join the list using empty string */
                    PyObject *tb_empty = dylib_python->PyUnicode_FromString("");
                    tb_str = dylib_python->PyUnicode_Join(tb_empty, tb);
                    dylib_python->Py_DecRef(tb_empty);
                    if (fmt_mode == PYI_TB_FMT_CRLF) {
                        /* Replace LF with CRLF */
                        PyObject *lf = dylib_python->PyUnicode_FromString("\n");
                        PyObject *crlf = dylib_python->PyUnicode_FromString("\r\n");
                        PyObject *tb_str_crlf = dylib_python->PyUnicode_Replace(tb_str, lf, crlf, -1);
                        dylib_python->Py_DecRef(lf);
                        dylib_python->Py_DecRef(crlf);
                        /* Swap */
                        dylib_python->Py_DecRef(tb_str);
                        tb_str = tb_str_crlf;
                    }
                }
            }
            if (tb_str != NULL) {
                tb_cchar = dylib_python->PyUnicode_AsUTF8(tb_str);
                if (tb_cchar) {
                    retval = strdup(tb_cchar);
                }
            }
            dylib_python->Py_DecRef(tb);
            dylib_python->Py_DecRef(tb_str);
        }
        dylib_python->Py_DecRef(func);
    }
    dylib_python->Py_DecRef(module);

    return retval;
}

#endif /* if defined(WINDOWED) */

/*
 * Run scripts
 * Return non zero on failure
 */
static int
_pyi_launch_run_scripts(const struct PYI_CONTEXT *pyi_ctx)
{
    const struct ARCHIVE *archive = pyi_ctx->archive;
    const struct DYLIB_PYTHON *dylib_python = pyi_ctx->dylib_python;
    unsigned char *data;
    char buf[PYI_PATH_MAX];
    const struct TOC_ENTRY *toc_entry;
    PyObject *__main__;
    PyObject *__file__;
    PyObject *main_dict;
    PyObject *code, *retval;

    __main__ = dylib_python->PyImport_AddModule("__main__");

    if (!__main__) {
        PYI_ERROR("Could not get __main__ module.\n");
        return -1;
    }

    main_dict = dylib_python->PyModule_GetDict(__main__);

    if (!main_dict) {
        PYI_ERROR("Could not get __main__ module's dict.\n");
        return -1;
    }

    /* Iterate through toc looking for scripts (type 's') */
    for (toc_entry = archive->toc; toc_entry < archive->toc_end; toc_entry = pyi_archive_next_toc_entry(archive, toc_entry)) {
        if (toc_entry->typecode != ARCHIVE_ITEM_PYSOURCE) {
            continue;
        }

        /* Get data out of the archive.  */
        data = pyi_archive_extract(archive, toc_entry);
        if (data == NULL) {
            PYI_ERROR("Failed to extract script from archive!\n");
            return -1;
        }

        /* Set the __file__ attribute within the __main__ module, for
         * full compatibility with normal execution. */
        if (snprintf(buf, PYI_PATH_MAX, "%s%c%s.py", pyi_ctx->application_home_dir, PYI_SEP, toc_entry->name) >= PYI_PATH_MAX) {
            PYI_ERROR("Absolute path to script exceeds PYI_PATH_MAX\n");
            return -1;
        }

        PYI_DEBUG("LOADER: running %s.py\n", toc_entry->name);

        __file__ = dylib_python->PyUnicode_FromString(buf);
        dylib_python->PyObject_SetAttrString(__main__, "__file__", __file__);
        dylib_python->Py_DecRef(__file__);

        /* Unmarshall code object */
        code = dylib_python->PyMarshal_ReadObjectFromString((const char *)data, toc_entry->uncompressed_length);
        free(data);
        if (!code) {
            PYI_ERROR("Failed to unmarshal code object for %s\n", toc_entry->name);
            dylib_python->PyErr_Print();
            return -1;
        }

        /* Store the code object to __main__ module's _pyi_main_co
         * attribute, so it can be retrieved by PyiFrozenEntryPointLoader,
         * if necessary. */
        dylib_python->PyObject_SetAttrString(__main__, "_pyi_main_co", code);

        /* Run it */
        retval = dylib_python->PyEval_EvalCode(code, main_dict, main_dict);

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
             * references to error indicator and its data. */
            PyObject *ptype, *pvalue, *ptraceback;
            char *msg_exc, *msg_tb;
            int fmt_mode = PYI_TB_FMT_REPR;

#if defined(_WIN32)
            fmt_mode = PYI_TB_FMT_CRLF;
#elif defined(__APPLE__)
            fmt_mode = PYI_TB_FMT_LF;
#endif

            dylib_python->PyErr_Fetch(&ptype, &pvalue, &ptraceback);
            dylib_python->PyErr_NormalizeException(&ptype, &pvalue, &ptraceback);
            msg_exc = _pyi_extract_exception_message(pvalue, dylib_python);
            if (pyi_ctx->disable_windowed_traceback) {
                /* Traceback is disabled via option */
                msg_tb = strdup("Traceback is disabled via bootloader option.");
            } else {
                msg_tb = _pyi_extract_exception_traceback(ptype, pvalue, ptraceback, fmt_mode, dylib_python);
            }
            dylib_python->PyErr_Restore(ptype, pvalue, ptraceback);
#endif /* defined(WINDOWED) */

            /* If the error was SystemExit, PyErr_Print calls exit() without
             * returning. This means we won't print "Failed to execute" on
             * normal SystemExit's. */
            dylib_python->PyErr_Print();

            /* Display error information */
#if !defined(WINDOWED)
            /* Non-windowed mode; PyErr_print() above dumps the
             * traceback, so the only thing we need to do here
             * is provide a summary */
            PYI_ERROR("Failed to execute script '%s' due to unhandled exception!\n", toc_entry->name);
#else /* !defined(WINDOWED) */
#if defined(_WIN32)
            /* Windows; use custom dialog */
            pyi_unhandled_exception_dialog(toc_entry->name, msg_exc, msg_tb);
#elif defined(__APPLE__)
            /* macOS .app bundle; use PYI_ERROR(), which
             * prints to stderr (invisible) as well as sends
             * the message to syslog */
            PYI_ERROR("Failed to execute script '%s' due to unhandled exception: %s\n", toc_entry->name, msg_exc);
            PYI_ERROR("Traceback:\n%s\n", msg_tb);
#endif /* defined(_WIN32) */

            /* Clean up exception information strings */
            free(msg_exc);
            free(msg_tb);
#endif /* if !defined(WINDOWED) */

            /* Be consistent with python interpreter, which returns
             * 1 if it exits due to unhandled exception. */
            return 1;
        }
    }

    return 0;
}

void
pyi_launch_initialize(struct PYI_CONTEXT *pyi_ctx)
{
    /* Nothing to do here at the moment. */
}

int
pyi_launch_execute(struct PYI_CONTEXT *pyi_ctx)
{
    int rc = 0;

    /* Load Python shared library and import symbols from it. */
    pyi_ctx->dylib_python = pyi_dylib_python_load(
        pyi_ctx->application_home_dir,
        pyi_ctx->archive->python_libname,
        pyi_ctx->archive->python_version
    );
    if (pyi_ctx->dylib_python == NULL) {
        return -1;
    }

    /* Start Python interpreter. */
    if (pyi_python_start_interpreter(pyi_ctx)) {
        return -1;
    }

    /* Import core pyinstaller modules from the executable - bootstrap */
    if (pyi_python_import_modules(pyi_ctx)) {
        return -1;
    }

    /* Install PYZ archive */
    if (pyi_python_install_pyz(pyi_ctx)) {
        return -1;
    }

    /* Run scripts */
    rc = _pyi_launch_run_scripts(pyi_ctx);

    if (rc == 0) {
        PYI_DEBUG("LOADER: OK.\n");
    } else {
        PYI_DEBUG("LOADER: ERROR.\n");
    }

    return rc;
}

void
pyi_launch_finalize(struct PYI_CONTEXT *pyi_ctx)
{
    /* CLean up the python interpreter */
    pyi_python_finalize(pyi_ctx);

    /* Unload python shared library */
    pyi_dylib_python_cleanup(&pyi_ctx->dylib_python);
}
