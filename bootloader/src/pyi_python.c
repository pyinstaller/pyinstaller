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
 * Functions to load, initialize and launch Python interpreter.
 */

#include <stdio.h>
#include <string.h>
#include <stdlib.h> /* free() */

/* PyInstaller headers. */
#include "pyi_python.h"
#include "pyi_global.h"
#include "pyi_path.h"
#include "pyi_archive.h"
#include "pyi_main.h"
#include "pyi_utils.h"
#include "pyi_dylib_python.h"
#include "pyi_pyconfig.h"


/*
 * Initialize and start python interpreter.
 */
int
pyi_python_start_interpreter(const struct PYI_CONTEXT *pyi_ctx)
{
    const struct DYLIB_PYTHON *dylib_python = pyi_ctx->dylib_python;
    struct PyiRuntimeOptions *runtime_options = NULL;
    PyConfig *config_pep587 = NULL; /* Config structure used in PEP 587 codepath */
    PyInitConfig *config_pep741 = NULL; /* Config structure used in PEP 741 codepath */
    int ret = -1;

    /* Read run-time options */
    runtime_options = pyi_runtime_options_read(pyi_ctx);
    if (runtime_options == NULL) {
        PYI_ERROR("Failed to parse run-time options!\n");
        goto end;
    }

    /* Pre-initialize python. This ensures that PEP 540 UTF-8 mode is enabled
     * if necessary. */
    PYI_DEBUG("LOADER: pre-initializing embedded python interpreter...\n");
    if (pyi_pyconfig_preinit_python(runtime_options, pyi_ctx) < 0) {
        PYI_ERROR("Failed to pre-initialize embedded python interpreter!\n");
        goto end;
    }

    /* Set up python configuration. */
    if (dylib_python->has_pep741) {
        /* PEP 741 codepath */
        PYI_DEBUG("LOADER: using PEP-741 API...\n");

        /* Allocate the config structure and initialize it using default values
         * of the Isolated Configuration. */
        PYI_DEBUG("LOADER: creating PyInitConfig structure...\n");
        config_pep741 = dylib_python->PyInitConfig_Create();
        if (config_pep741 == NULL) {
            PYI_ERROR("Failed to allocate PyInitConfig structure!\n");
            goto end;
        }

        /* Set program name */
        PYI_DEBUG("LOADER: setting program name...\n");
        if (pyi_pyconfig_pep741_set_program_name(config_pep741, pyi_ctx) < 0) {
            PYI_ERROR("Failed to set program name!\n");
            goto end;
        }

        /* Set python home */
        PYI_DEBUG("LOADER: setting python home path...\n");
        if (pyi_pyconfig_pep741_set_python_home(config_pep741, pyi_ctx) < 0) {
            PYI_ERROR("Failed to set python home path!\n");
            goto end;
        }

        /* Set module search paths */
        PYI_DEBUG("LOADER: setting module search paths...\n");
        if (pyi_pyconfig_pep741_set_module_search_paths(config_pep741, pyi_ctx) < 0) {
            PYI_ERROR("Failed to set module search paths!\n");
            goto end;
        }

        /* Set arguments (sys.argv) */
        PYI_DEBUG("LOADER: setting sys.argv...\n");
        if (pyi_pyconfig_pep741_set_argv(config_pep741, pyi_ctx) < 0) {
            PYI_ERROR("Failed to set sys.argv!\n");
            goto end;
        }

        /* Apply run-time options */
        PYI_DEBUG("LOADER: applying run-time options...\n");
        if (pyi_pyconfig_pep741_set_runtime_options(config_pep741, pyi_ctx, runtime_options) < 0) {
            PYI_ERROR("Failed to set run-time options!\n");
            goto end;
        }
    } else {
        /* PEP 587 codepath */
        PYI_DEBUG("LOADER: using PEP-587 API...\n");

        /* Allocate the config structure. Since underlying layout is specific to
         * python version, this also verifies that python version is supported. */
        PYI_DEBUG("LOADER: creating PyConfig structure...\n");
        config_pep587 = pyi_pyconfig_pep587_create(pyi_ctx);
        if (config_pep587 == NULL) {
            PYI_ERROR("Failed to allocate PyConfig structure! Unsupported python version?\n");
            goto end;
        }

        /* Initialize isolated configuration */
        PYI_DEBUG("LOADER: initializing interpreter configuration...\n");
        dylib_python->PyConfig_InitIsolatedConfig(config_pep587);

        /* Set program name */
        PYI_DEBUG("LOADER: setting program name...\n");
        if (pyi_pyconfig_pep587_set_program_name(config_pep587, pyi_ctx) < 0) {
            PYI_ERROR("Failed to set program name!\n");
            goto end;
        }

        /* Set python home */
        PYI_DEBUG("LOADER: setting python home path...\n");
        if (pyi_pyconfig_pep587_set_python_home(config_pep587, pyi_ctx) < 0) {
            PYI_ERROR("Failed to set python home path!\n");
            goto end;
        }

        /* Set module search paths */
        PYI_DEBUG("LOADER: setting module search paths...\n");
        if (pyi_pyconfig_pep587_set_module_search_paths(config_pep587, pyi_ctx) < 0) {
            PYI_ERROR("Failed to set module search paths!\n");
            goto end;
        }

        /* Set arguments (sys.argv) */
        PYI_DEBUG("LOADER: setting sys.argv...\n");
        if (pyi_pyconfig_pep587_set_argv(config_pep587, pyi_ctx) < 0) {
            PYI_ERROR("Failed to set sys.argv!\n");
            goto end;
        }

        /* Apply run-time options */
        PYI_DEBUG("LOADER: applying run-time options...\n");
        if (pyi_pyconfig_pep587_set_runtime_options(config_pep587, pyi_ctx, runtime_options) < 0) {
            PYI_ERROR("Failed to set run-time options!\n");
            goto end;
        }
    }

    /* Start the interpreter */
    PYI_DEBUG("LOADER: starting embedded python interpreter...\n");

    /* In unbuffered mode, flush stdout/stderr before python configuration
     * removes the buffer (changing the buffer should probably flush the
     * old buffer, but just in case do it manually...) */
    if (runtime_options->unbuffered) {
        fflush(stdout);
        fflush(stderr);
    }

    if (dylib_python->has_pep741) {
        /* PEP 741 codepath */
        ret = dylib_python->Py_InitializeFromInitConfig(config_pep741);
        if (ret < 0) {
            const char *error_message = NULL;
            dylib_python->PyInitConfig_GetError(config_pep741, &error_message);
            PYI_ERROR("Failed to start embedded python interpreter: %s\n", error_message);
            ret = -1;
        }
    } else {
        /* PEP 587 codepath */
        PyStatus status;

        status = dylib_python->Py_InitializeFromConfig(config_pep587);

        if (dylib_python->PyStatus_Exception(status)) {
            PYI_ERROR("Failed to start embedded python interpreter!\n");
            /* Dump exception information to stderr and exit the process with error code.
             *
             * Depending on the error type, Py_ExitStatusException() either
             * ends up calling exit() or abort(). On Windows, the latter case
             * triggers the error reporting service and pops up a dialog with
             * "Close program", "Check for a solution", and "Debug" (if Visual
             * Studio is installed). Disable this behavior via SetErrorMode() */
#if defined(_WIN32)
            SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX);
#endif
            dylib_python->Py_ExitStatusException(status);
            /* Not reachable; Py_ExitStatusException() either calls exit() or
             * abort(). */
        } else {
            ret = 0; /* Succeeded */
        }
    }

end:
    if (dylib_python->has_pep741) {
        /* PEP 741 codepath */
        dylib_python->PyInitConfig_Free(config_pep741);
    } else {
        /* PEP 587 codepath */
        pyi_pyconfig_pep587_free(config_pep587, pyi_ctx);
    }
    pyi_runtime_options_free(runtime_options);
    return ret;
}

/*
 * Import (bootstrap) modules embedded in the PKG archive.
 */
int
pyi_python_import_modules(const struct PYI_CONTEXT *pyi_ctx)
{
    const struct DYLIB_PYTHON *dylib_python = pyi_ctx->dylib_python;
    const struct ARCHIVE *archive = pyi_ctx->archive;
    const struct TOC_ENTRY *toc_entry;
    unsigned char *data;
    PyObject *co;
    PyObject *mod;
    PyObject *meipass_obj;

    PYI_DEBUG("LOADER: setting sys._MEIPASS\n");

#ifdef _WIN32
    meipass_obj = dylib_python->PyUnicode_Decode(pyi_ctx->application_home_dir, strlen(pyi_ctx->application_home_dir), "utf-8", "strict");
#else
    meipass_obj = dylib_python->PyUnicode_DecodeFSDefault(pyi_ctx->application_home_dir);
#endif

    if (!meipass_obj) {
        PYI_ERROR("Failed to get _MEIPASS as PyObject.\n");
        return -1;
    }

    dylib_python->PySys_SetObject("_MEIPASS", meipass_obj);

    PYI_DEBUG("LOADER: importing modules from PKG/CArchive\n");

    /* Iterate through toc looking for module entries (type 'm')
     * this is normally just bootstrap stuff (archive and iu) */
    for (toc_entry = archive->toc; toc_entry < archive->toc_end; toc_entry = pyi_archive_next_toc_entry(archive, toc_entry)) {
        if (toc_entry->typecode != ARCHIVE_ITEM_PYMODULE && toc_entry->typecode != ARCHIVE_ITEM_PYPACKAGE) {
            continue;
        }

        data = pyi_archive_extract(archive, toc_entry);
        PYI_DEBUG("LOADER: extracted %s\n", toc_entry->name);

        /* Unmarshal the stored code object */
        co = dylib_python->PyMarshal_ReadObjectFromString((const char *)data, toc_entry->uncompressed_length);
        free(data);

        if (co == NULL) {
            PYI_ERROR("Failed to unmarshal code object for module %s!\n", toc_entry->name);
            mod = NULL;
        } else {
            PYI_DEBUG("LOADER: running unmarshalled code object for module %s...\n", toc_entry->name);
            mod = dylib_python->PyImport_ExecCodeModule(toc_entry->name, co);
            if (mod == NULL) {
                PYI_ERROR("Module object for %s is NULL!\n", toc_entry->name);
            }
        }

        if (dylib_python->PyErr_Occurred()) {
            dylib_python->PyErr_Print();
            dylib_python->PyErr_Clear();
        }

        /* Exit on error */
        if (mod == NULL) {
            return -1;
        }
    }

    return 0;
}

/*
 * Store path and offset to PYZ archive into sys._pyinstaller_pyz
 * attribute, so that our bootstrap python script can set up PYZ
 * archive reader.
 */
int
pyi_python_install_pyz(const struct PYI_CONTEXT *pyi_ctx)
{
    const struct DYLIB_PYTHON *dylib_python = pyi_ctx->dylib_python;
    const struct ARCHIVE *archive = pyi_ctx->archive;
    const struct TOC_ENTRY *toc_entry;
    PyObject *archive_filename_obj;
    PyObject *pyz_path_obj;
    unsigned long long pyz_offset;
    int rc;
    const char *attr_name = "_pyinstaller_pyz";

    PYI_DEBUG("LOADER: looking for PYZ archive TOC entry...\n");

    /* Iterate through TOC and look for PYZ entry (type 'z') */
    for (toc_entry = archive->toc; toc_entry < archive->toc_end; toc_entry = pyi_archive_next_toc_entry(archive, toc_entry)) {
        if (toc_entry->typecode == ARCHIVE_ITEM_PYZ) {
            break;
        }
    }
    if (toc_entry >= archive->toc_end) {
        PYI_ERROR("PYZ archive entry not found in the TOC!\n");
        return -1;
    }

    /* Store archive filename as Python string. */
#ifdef _WIN32
    /* Decode UTF-8 to PyUnicode */
    archive_filename_obj = dylib_python->PyUnicode_Decode(pyi_ctx->archive_filename, strlen(pyi_ctx->archive_filename), "utf-8", "strict");
#else
    /* Decode locale-encoded filename to PyUnicode object using Python's
     * preferred decoding method for filenames. */
    archive_filename_obj = dylib_python->PyUnicode_DecodeFSDefault(pyi_ctx->archive_filename);
#endif

    /* Format name plus offset; here, we assume that python's %llu format
     * matches the platform's definition of "unsigned long long". Of
     * which we actually have no guarantee, but thankfully that does
     * seem to be the case. */
    pyz_offset = pyi_ctx->archive->pkg_offset + toc_entry->offset;
    pyz_path_obj = dylib_python->PyUnicode_FromFormat("%U?%llu", archive_filename_obj, pyz_offset);
    dylib_python->Py_DecRef(archive_filename_obj);

    if (pyz_path_obj == NULL) {
        PYI_ERROR("Failed to format PYZ archive path and offset\n");
        return -1;
    }

    /* Store into sys._pyinstaller_pyz */
    rc = dylib_python->PySys_SetObject(attr_name, pyz_path_obj);
    dylib_python->Py_DecRef(pyz_path_obj);

    if (rc != 0) {
        PYI_ERROR("Failed to store path to PYZ archive into sys.%s!\n", attr_name);
        return -1;
    }

    PYI_DEBUG("LOADER: path to PYZ archive stored into sys.%s...\n", attr_name);
    return 0;
}

void
pyi_python_finalize(const struct PYI_CONTEXT *pyi_ctx)
{
    const struct DYLIB_PYTHON *dylib_python = pyi_ctx->dylib_python;

    /* Ensure python library was loaded; otherwise PI_* function pointers
     * are invalid, and we have nothing to do here. */
    if (!dylib_python) {
        return;
    }

    /* Nothing to do if python interpreter was not initialized. Attempting
     * to flush streams using PyRun_SimpleStringFlags requires a valid
     * interpreter instance. */
    if (dylib_python->Py_IsInitialized() == 0) {
        return;
    }

#ifndef WINDOWED
    /* We need to manually flush the buffers because otherwise there can be errors.
     * The native python interpreter flushes buffers before calling Py_Finalize,
     * so we need to manually do the same. See isse #4908. */
    PYI_DEBUG("LOADER: manually flushing stdout and stderr...\n");

    /* sys.stdout.flush() */
    dylib_python->PyRun_SimpleStringFlags(
        "import sys; sys.stdout.flush(); \
        (sys.__stdout__.flush if sys.__stdout__ \
        is not sys.stdout else (lambda: None))()", NULL);

    /* sys.stderr.flush() */
    dylib_python->PyRun_SimpleStringFlags(
        "import sys; sys.stderr.flush(); \
        (sys.__stderr__.flush if sys.__stderr__ \
        is not sys.stderr else (lambda: None))()", NULL);

#endif

    /* Finalize the interpreter. This calls all of the atexit functions. */
    PYI_DEBUG("LOADER: cleaning up Python interpreter...\n");
    dylib_python->Py_Finalize();
}
