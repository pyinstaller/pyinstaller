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
 * Functions to load, initialize and launch Python.
 */
/* size of buffer to store the name of the Python shared library */
#define MAX_DLL_NAME_LEN 64

#ifdef _WIN32
    #include <windows.h> /* HMODULE */
#else
    #include <dlfcn.h>  /* dlerror */
    #include <stdlib.h>  /* mbstowcs */
#endif /* ifdef _WIN32 */
#include <stddef.h>  /* ptrdiff_t */
#include <stdio.h>
#include <string.h>

/* PyInstaller headers. */
#include "pyi_pythonlib.h"
#include "pyi_global.h"
#include "pyi_path.h"
#include "pyi_archive.h"
#include "pyi_main.h"
#include "pyi_utils.h"
#include "pyi_python.h"
#include "pyi_pyconfig.h"

/*
 * Load the Python shared library, and bind all required symbols from it.
 */
int
pyi_pylib_load(struct PYI_CONTEXT *pyi_ctx)
{
    const struct ARCHIVE *archive = pyi_ctx->archive;
    char dll_name[MAX_DLL_NAME_LEN];
    size_t dll_name_len;
    char dll_fullpath[PYI_PATH_MAX];

    /* On AIX, the name of shared library path might be an archive, because
     * the 'ar' archives can be used for both static and shared objects.
     * A shared library can be loaded from such an archive like this:
     *   dlopen("libpythonX.Y.a(libpythonX.Y.so)", RTLD_MEMBER)
     * This means that if python library name ends with '.a' suffix, we
     * need to change it into:
     *   libpython3.6.a(libpython3.6.so)
     * Shared libraries whose names end with .so may be used as-is. */
#ifdef AIX
    /* Determine if shared lib is in `libpython?.?.so` or
     * `libpython?.?.a(libpython?.?.so)` format. */
    char *p;
    if ((p = strrchr(archive->python_libname, '.')) != NULL && strcmp(p, ".a") == 0) {
        uint32_t pyver_major;
        uint32_t pyver_minor;

        pyver_major = archive->python_version / 100;
        pyver_minor = archive->python_version % 100;

        dll_name_len = snprintf(
            dll_name,
            MAX_DLL_NAME_LEN,
            "libpython%d.%d.a(libpython%d.%d.so)",
            pyver_major,
            pyver_minor,
            pyver_major,
            pyver_minor
        );
    } else {
        dll_name_len = snprintf(dll_name, MAX_DLL_NAME_LEN, "%s", archive->python_libname);
    }
#else
    dll_name_len = snprintf(dll_name, MAX_DLL_NAME_LEN, "%s", archive->python_libname);
#endif

    if (dll_name_len >= MAX_DLL_NAME_LEN) {
        PYI_ERROR(
            "Reported length (%d) of Python shared library name (%s) exceeds buffer size (%d)\n",
            dll_name_len,
            archive->python_libname,
            MAX_DLL_NAME_LEN
        );
        return -1;
    }

#ifdef _WIN32
    /* If ucrtbase.dll exists in top-level application directory, load
     * it proactively before Python library loading to avoid Python library
     * loading failure (unresolved symbol errors) on systems with Universal
     * CRT update not installed. */
    if (1) {
        char ucrtpath[PYI_PATH_MAX];
        if (pyi_path_join(ucrtpath, pyi_ctx->application_home_dir, "ucrtbase.dll") == NULL) {
            PYI_ERROR("Path of ucrtbase.dll (%s) and its name exceed buffer size (%d)\n", pyi_ctx->application_home_dir, PYI_PATH_MAX);
        }
        if (pyi_path_exists(ucrtpath)) {
            PYI_DEBUG("LOADER: ucrtbase.dll found: %s\n", ucrtpath);
            pyi_utils_dlopen(ucrtpath);
        }
    }
#endif

    /* Look for python shared library in top-level application directory */
    if (pyi_path_join(dll_fullpath, pyi_ctx->application_home_dir, dll_name) == NULL) {
        PYI_ERROR("Path of Python shared library (%s) and its name (%s) exceed buffer size (%d)\n", pyi_ctx->application_home_dir, PYI_PATH_MAX);
        return -1;
    }

    PYI_DEBUG("LOADER: loading Python shared library: %s\n", dll_fullpath);

    /* Load the shared libary */
    pyi_ctx->python_dll = pyi_utils_dlopen(dll_fullpath);

    if (pyi_ctx->python_dll == 0) {
#ifdef _WIN32
        wchar_t dll_fullpath_w[PYI_PATH_MAX];
        pyi_win32_utf8_to_wcs(dll_fullpath, dll_fullpath_w, PYI_PATH_MAX);
        PYI_WINERROR_W(L"LoadLibrary", L"Failed to load Python DLL '%ls'.\n", dll_fullpath_w);
#else
        PYI_ERROR("Failed to load Python shared library '%s': dlopen: %s\n", dll_fullpath, dlerror());
#endif
        return -1;
    }

    return pyi_python_bind_functions(pyi_ctx->python_dll, archive->python_version);
}

/*
 * Initialize and start python interpreter.
 */
int
pyi_pylib_start_python(const struct PYI_CONTEXT *pyi_ctx)
{
    struct PyiRuntimeOptions *runtime_options = NULL;
    PyConfig *config = NULL;
    PyStatus status;
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
    if (pyi_pyconfig_preinit_python(runtime_options) < 0) {
        PYI_ERROR("Failed to pre-initialize embedded python interpreter!\n");
        goto end;
    }

    /* Allocate the config structure. Since underlying layout is specific to
     * python version, this also verifies that python version is supported. */
    PYI_DEBUG("LOADER: creating PyConfig structure...\n");
    config = pyi_pyconfig_create(pyi_ctx);
    if (config == NULL) {
        PYI_ERROR("Failed to allocate PyConfig structure! Unsupported python version?\n");
        goto end;
    }

    /* Initialize isolated configuration */
    PYI_DEBUG("LOADER: initializing interpreter configuration...\n");
    PI_PyConfig_InitIsolatedConfig(config);

    /* Set program name */
    PYI_DEBUG("LOADER: setting program name...\n");
    if (pyi_pyconfig_set_program_name(config, pyi_ctx) < 0) {
        PYI_ERROR("Failed to set program name!\n");
        goto end;
    }

    /* Set python home */
    PYI_DEBUG("LOADER: setting python home path...\n");
    if (pyi_pyconfig_set_python_home(config, pyi_ctx) < 0) {
        PYI_ERROR("Failed to set python home path!\n");
        goto end;
    }

    /* Set module search paths */
    PYI_DEBUG("LOADER: setting module search paths...\n");
    if (pyi_pyconfig_set_module_search_paths(config, pyi_ctx) < 0) {
        PYI_ERROR("Failed to set module search paths!\n");
        goto end;
    }

    /* Set arguments (sys.argv) */
    PYI_DEBUG("LOADER: setting sys.argv...\n");
    if (pyi_pyconfig_set_argv(config, pyi_ctx) < 0) {
        PYI_ERROR("Failed to set sys.argv!\n");
        goto end;
    }

    /* Apply run-time options */
    PYI_DEBUG("LOADER: applying run-time options...\n");
    if (pyi_pyconfig_set_runtime_options(config, pyi_ctx, runtime_options) < 0) {
        PYI_ERROR("Failed to set run-time options!\n");
        goto end;
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

    /*
     * Py_Initialize() may rudely call abort(), and on Windows this triggers the error
     * reporting service, which results in a dialog box that says "Close program", "Check
     * for a solution", and also "Debug" if Visual Studio is installed. The dialog box
     * makes it frustrating to run the test suite.
     *
     * For debug builds of the bootloader, disable the error reporting before calling
     * Py_Initialize and enable it afterward.
     */

#if defined(_WIN32) && defined(LAUNCH_DEBUG)
    SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX);
#endif

    status = PI_Py_InitializeFromConfig(config);

#if defined(_WIN32) && defined(LAUNCH_DEBUG)
    SetErrorMode(0);
#endif

    if (PI_PyStatus_Exception(status)) {
        PYI_ERROR("Failed to start embedded python interpreter!\n");
        /* Dump exception information to stderr and exit the process with error code. */
        PI_Py_ExitStatusException(status);
    } else {
        ret = 0; /* Succeeded */
    }

end:
    pyi_pyconfig_free(config);
    pyi_runtime_options_free(runtime_options);
    return ret;
}

/*
 * Import (bootstrap) modules embedded in the PKG archive.
 */
int
pyi_pylib_import_modules(const struct PYI_CONTEXT *pyi_ctx)
{
    const struct ARCHIVE *archive = pyi_ctx->archive;
    const struct TOC_ENTRY *toc_entry;
    unsigned char *data;
    PyObject *co;
    PyObject *mod;
    PyObject *meipass_obj;

    PYI_DEBUG("LOADER: setting sys._MEIPASS\n");

    /* TODO extract function pyi_char_to_pyobject */
#ifdef _WIN32
    meipass_obj = PI_PyUnicode_Decode(pyi_ctx->application_home_dir, strlen(pyi_ctx->application_home_dir), "utf-8", "strict");
#else
    meipass_obj = PI_PyUnicode_DecodeFSDefault(pyi_ctx->application_home_dir);
#endif

    if (!meipass_obj) {
        PYI_ERROR("Failed to get _MEIPASS as PyObject.\n");
        return -1;
    }

    PI_PySys_SetObject("_MEIPASS", meipass_obj);

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
        co = PI_PyMarshal_ReadObjectFromString((const char *)data, toc_entry->uncompressed_length);
        free(data);

        if (co == NULL) {
            PYI_ERROR("Failed to unmarshal code object for module %s!\n", toc_entry->name);
            mod = NULL;
        } else {
            PYI_DEBUG("LOADER: running unmarshalled code object for module %s...\n", toc_entry->name);
            mod = PI_PyImport_ExecCodeModule(toc_entry->name, co);
            if (mod == NULL) {
                PYI_ERROR("Module object for %s is NULL!\n", toc_entry->name);
            }
        }

        if (PI_PyErr_Occurred()) {
            PI_PyErr_Print();
            PI_PyErr_Clear();
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
pyi_pylib_install_pyz(const struct PYI_CONTEXT *pyi_ctx)
{
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
    archive_filename_obj = PI_PyUnicode_Decode(pyi_ctx->archive_filename, strlen(pyi_ctx->archive_filename), "utf-8", "strict");
#else
    /* Decode locale-encoded filename to PyUnicode object using Python's
     * preferred decoding method for filenames. */
    archive_filename_obj = PI_PyUnicode_DecodeFSDefault(pyi_ctx->archive_filename);
#endif

    /* Format name plus offset; here, we assume that python's %llu format
     * matches the platform's definition of "unsigned long long". Of
     * which we actually have no guarantee, but thankfully that does
     * seem to be the case. */
    pyz_offset = pyi_ctx->archive->pkg_offset + toc_entry->offset;
    pyz_path_obj = PI_PyUnicode_FromFormat("%U?%llu", archive_filename_obj, pyz_offset);
    PI_Py_DecRef(archive_filename_obj);

    if (pyz_path_obj == NULL) {
        PYI_ERROR("Failed to format PYZ archive path and offset\n");
        return -1;
    }

    /* Store into sys._pyinstaller_pyz */
    rc = PI_PySys_SetObject(attr_name, pyz_path_obj);
    PI_Py_DecRef(pyz_path_obj);

    if (rc != 0) {
        PYI_ERROR("Failed to store path to PYZ archive into sys.%s!\n", attr_name);
        return -1;
    }

    PYI_DEBUG("LOADER: path to PYZ archive stored into sys.%s...\n", attr_name);
    return 0;
}

void
pyi_pylib_finalize(const struct PYI_CONTEXT *pyi_ctx)
{
    /* Ensure python library was loaded; otherwise PI_* function pointers
     * are invalid, and we have nothing to do here. */
    if (!pyi_ctx->python_symbols_loaded) {
        return;
    }

    /* Nothing to do if python interpreter was not initialized. Attempting
     * to flush streams using PyRun_SimpleStringFlags requires a valid
     * interpreter instance. */
    if (PI_Py_IsInitialized() == 0) {
        return;
    }

#ifndef WINDOWED
    /* We need to manually flush the buffers because otherwise there can be errors.
     * The native python interpreter flushes buffers before calling Py_Finalize,
     * so we need to manually do the same. See isse #4908. */
    PYI_DEBUG("LOADER: manually flushing stdout and stderr...\n");

    /* sys.stdout.flush() */
    PI_PyRun_SimpleStringFlags(
        "import sys; sys.stdout.flush(); \
        (sys.__stdout__.flush if sys.__stdout__ \
        is not sys.stdout else (lambda: None))()", NULL);

    /* sys.stderr.flush() */
    PI_PyRun_SimpleStringFlags(
        "import sys; sys.stderr.flush(); \
        (sys.__stderr__.flush if sys.__stderr__ \
        is not sys.stderr else (lambda: None))()", NULL);

#endif

    /* Finalize the interpreter. This calls all of the atexit functions. */
    PYI_DEBUG("LOADER: cleaning up Python interpreter...\n");
    PI_Py_Finalize();
}
