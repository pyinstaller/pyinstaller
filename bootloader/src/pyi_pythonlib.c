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
/* size of buffer to store the name of the Python DLL library */
#define DLLNAME_LEN (64)

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
#include "pyi_utils.h"
#include "pyi_python.h"
#include "pyi_win32_utils.h"
#include "pyi_pyconfig.h"

/*
 * Load the Python shared library, and bind all required functions from it.
 */
int
pyi_pylib_load(const ARCHIVE_STATUS *archive_status)
{
    dylib_t dll;
    char dllpath[PATH_MAX];
    char dllname[DLLNAME_LEN];
    size_t len;

/*
 * On AIX Append the name of shared object library path might be an archive.
 * In that case, modify the name to make it look like:
 *   libpython3.6.a(libpython3.6.so)
 * Shared object names ending with .so may be used asis.
 */
#ifdef AIX
    /*
     * Determine if shared lib is in libpython?.?.so or
     * libpython?.?.a(libpython?.?.so) format
     */
    char *p;
    if ((p = strrchr(archive_status->cookie.pylibname, '.')) != NULL && strcmp(p, ".a") == 0) {
      /*
       * On AIX 'ar' archives are used for both static and shared object.
       * To load a shared object from a library, it should be loaded like this:
       *   dlopen("libpythonX.Y.a(libpythonX.Y.so)", RTLD_MEMBER)
       */
      uint32_t pyvers_major;
      uint32_t pyvers_minor;

      pyvers_major = pyvers / 100;
      pyvers_minor = pyvers % 100;

      len = snprintf(dllname, DLLNAME_LEN,
              "libpython%d.%d.a(libpython%d.%d.so)",
              pyvers_major, pyvers_minor, pyvers_major, pyvers_minor);
    }
    else {
      len = snprintf(dllname, DLLNAME_LEN, "%s", archive_status->cookie.pylibname);
    }
#else
    len = snprintf(dllname, DLLNAME_LEN, "%s", archive_status->cookie.pylibname);
#endif

    if (len >= DLLNAME_LEN) {
        FATALERROR("Reported length (%d) of DLL name (%s) length exceeds buffer[%d] space\n",
                   len, archive_status->cookie.pylibname, DLLNAME_LEN);
        return -1;
    }

#ifdef _WIN32
    /*
     * If ucrtbase.dll exists in temppath, load it proactively before Python
     * library loading to avoid Python library loading failure (unresolved
     * symbol errors) on systems with Universal CRT update not installed.
     */
    if (archive_status->has_temp_directory) {
        char ucrtpath[PATH_MAX];
        if (pyi_path_join(ucrtpath, archive_status->temppath, "ucrtbase.dll") == NULL) {
            FATALERROR("Path of ucrtbase.dll (%s) length exceeds buffer[%d] space\n", archive_status->temppath, PATH_MAX);
        }
        if (pyi_path_exists(ucrtpath)) {
            VS("LOADER: ucrtbase.dll found: %s\n", ucrtpath);
            pyi_utils_dlopen(ucrtpath);
        }
    }
#endif

    /*
     * Look for Python library in homepath or temppath.
     * It depends on the value of mainpath.
     */
    if (pyi_path_join(dllpath, archive_status->mainpath, dllname) == NULL) {
        FATALERROR("Path of DLL (%s) length exceeds buffer[%d] space\n", archive_status->mainpath, PATH_MAX);
    };

    VS("LOADER: Python library: %s\n", dllpath);

    /* Load the DLL */
    dll = pyi_utils_dlopen(dllpath);

    /* Check success of loading Python library. */
    if (dll == 0) {
#ifdef _WIN32
        FATAL_WINERROR("LoadLibrary", "Error loading Python DLL '%s'.\n", dllpath);
#else
        FATALERROR("Error loading Python lib '%s': dlopen: %s\n",
                   dllpath, dlerror());
#endif
        return -1;
    }

    return pyi_python_bind_functions(dll, pyvers);
}

/*
 * Initialize and start python interpreter.
 */
int
pyi_pylib_start_python(const ARCHIVE_STATUS *archive_status)
{
    PyiRuntimeOptions *runtime_options = NULL;
    PyConfig *config = NULL;
    PyStatus status;
    int ret = -1;

    /* Read run-time options */
    runtime_options = pyi_runtime_options_read(archive_status);
    if (runtime_options == NULL) {
        FATALERROR("Failed to parse run-time options!\n");
        goto end;
    }

    /* Pre-initialize python. This ensures that PEP 540 UTF-8 mode is enabled
     * if necessary. */
    VS("LOADER: Pre-initializing embedded python interpreter...\n");
    if (pyi_pyconfig_preinit_python(runtime_options) < 0) {
        FATALERROR("Failed to pre-initialize embedded python interpreter!\n");
        goto end;
    }

    /* Allocate the config structure. Since underlying layout is specific to
     * python version, this also verifies that python version is supported. */
    VS("LOADER: Creating PyConfig structure...\n");
    config = pyi_pyconfig_create();
    if (config == NULL) {
        FATALERROR("Failed to allocate PyConfig structure! Unsupported python version?\n");
        goto end;
    }

    /* Initialize isolated configuration */
    VS("LOADER: Initializing interpreter configuration...\n");
    PI_PyConfig_InitIsolatedConfig(config);

    /* Set program name */
    VS("LOADER: Setting program name...\n");
    if (pyi_pyconfig_set_program_name(config, archive_status) < 0) {
        FATALERROR("Failed to set program name!\n");
        goto end;
    }

    /* Set python home */
    VS("LOADER: Setting python home path...\n");
    if (pyi_pyconfig_set_python_home(config, archive_status) < 0) {
        FATALERROR("Failed to set python home path!\n");
        goto end;
    }

    /* Set module search paths */
    VS("LOADER: Setting module search paths...\n");
    if (pyi_pyconfig_set_module_search_paths(config, archive_status) < 0) {
        FATALERROR("Failed to set module search paths!\n");
        goto end;
    }

    /* Set arguments (sys.argv) */
    VS("LOADER: Setting sys.argv...\n");
    if (pyi_pyconfig_set_argv(config, archive_status) < 0) {
        FATALERROR("Failed to set sys.argv!\n");
        goto end;
    }

    /* Apply run-time options */
    VS("LOADER: Applying run-time options...\n");
    if (pyi_pyconfig_set_runtime_options(config, runtime_options) < 0) {
        FATALERROR("Failed to set run-time options!\n");
        goto end;
    }

    /* Start the interpreter */
    VS("LOADER: Starting embedded python interpreter...\n");

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
        FATALERROR("Failed to start embedded python interpreter!\n");
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
pyi_pylib_import_modules(ARCHIVE_STATUS *archive_status)
{
    const TOC *ptoc;
    PyObject *co;
    PyObject *mod;
    PyObject *meipass_obj;

    VS("LOADER: setting sys._MEIPASS\n");

    /* TODO extract function pyi_char_to_pyobject */
#ifdef _WIN32
    meipass_obj = PI_PyUnicode_Decode(archive_status->mainpath, strlen(archive_status->mainpath), "utf-8", "strict");
#else
    meipass_obj = PI_PyUnicode_DecodeFSDefault(archive_status->mainpath);
#endif

    if (!meipass_obj) {
        FATALERROR("Failed to get _MEIPASS as PyObject.\n");
        return -1;
    }

    PI_PySys_SetObject("_MEIPASS", meipass_obj);

    VS("LOADER: importing modules from CArchive\n");

    /* Iterate through toc looking for module entries (type 'm')
     * this is normally just bootstrap stuff (archive and iu) */
    ptoc = archive_status->tocbuff;
    while (ptoc < archive_status->tocend) {
        if (ptoc->typcd == ARCHIVE_ITEM_PYMODULE || ptoc->typcd == ARCHIVE_ITEM_PYPACKAGE) {
            unsigned char *modbuf = pyi_arch_extract(archive_status, ptoc);

            VS("LOADER: extracted %s\n", ptoc->name);

            /* Unmarshal the stored code object */
            co = PI_PyMarshal_ReadObjectFromString((const char *)modbuf, ptoc->ulen);

            if (co != NULL) {
                VS("LOADER: running unmarshalled code object for %s...\n", ptoc->name);
                mod = PI_PyImport_ExecCodeModule(ptoc->name, co);
            }
            else {
                VS("LOADER: failed to unmarshal code object for %s!\n", ptoc->name);
                mod = NULL;
            }

            /* Check for errors in loading */
            if (mod == NULL) {
                FATALERROR("Module object for %s is NULL!\n", ptoc->name);
            }

            if (PI_PyErr_Occurred()) {
                PI_PyErr_Print();
                PI_PyErr_Clear();
            }

            free(modbuf);

            /* Exit on error */
            if (mod == NULL) {
                return -1;
            }
        }
        ptoc = pyi_arch_increment_toc_ptr(archive_status, ptoc);
    }

    return 0;
}

/*
 * Install a PYZ from a TOC entry, by adding it to sys.path.
 *
 * Must be called after Py_Initialize (i.e. after pyi_pylib_start_python)
 *
 * The installation is done by adding an entry like
 *    absolute_path/dist/hello_world/hello_world?123456
 * to sys.path. The end number is the offset where the
 * Python-side bootstrap code should read the PYZ data.
 * Return non zero on failure.
 * NB: This entry is removed from sys.path by the Python-side bootstrap scripts.
 */
int
_pyi_pylib_install_pyz_entry(const ARCHIVE_STATUS *archive_status, const TOC *ptoc)
{
    int rc = 0;
    unsigned long long zlibpos = archive_status->pkgstart + ptoc->pos;
    PyObject * sys_path, *zlib_entry, *archivename_obj;

    /* Note that sys.path contains PyUnicode on py3. Ensure
     * that filenames are encoded or decoded correctly. */
#ifdef _WIN32
    /* Decode UTF-8 to PyUnicode */
    archivename_obj = PI_PyUnicode_Decode(archive_status->archivename, strlen(archive_status->archivename), "utf-8", "strict");
#else
    /* Decode locale-encoded filename to PyUnicode object using Python's
     * preferred decoding method for filenames. */
    archivename_obj = PI_PyUnicode_DecodeFSDefault(archive_status->archivename);
#endif
    zlib_entry = PI_PyUnicode_FromFormat("%U?%llu", archivename_obj, zlibpos);
    PI_Py_DecRef(archivename_obj);

    sys_path = PI_PySys_GetObject("path");

    if (sys_path == NULL) {
        FATALERROR("Installing PYZ: Could not get sys.path!\n");
        PI_Py_DecRef(zlib_entry);
        return -1;
    }

    rc = PI_PyList_Append(sys_path, zlib_entry);
    if (rc != 0) {
        FATALERROR("Failed to append PYZ entry to sys.path!\n");
    }

    return rc;
}

/*
 * Install PYZ archive(s) to sys.path.
 * Return non zero on failure.
 */
int
pyi_pylib_install_pyz(const ARCHIVE_STATUS *archive_status)
{
    const TOC *ptoc;

    VS("LOADER: Installing PYZ archive with Python modules.\n");

    /* Iterate through TOC looking for PYZ (type 'z') */
    ptoc = archive_status->tocbuff;
    while (ptoc < archive_status->tocend) {
        if (ptoc->typcd == ARCHIVE_ITEM_PYZ) {
            VS("LOADER: PYZ archive: %s\n", ptoc->name);
            if (_pyi_pylib_install_pyz_entry(archive_status, ptoc) < 0) {
                return -1;
            }
        }

        ptoc = pyi_arch_increment_toc_ptr(archive_status, ptoc);
    }
    return 0;
}

void
pyi_pylib_finalize(const ARCHIVE_STATUS *archive_status)
{
    /* Ensure python library was loaded; otherwise PI_* function pointers
     * are invalid, and we have nothing to do here. */
    if (archive_status->is_pylib_loaded != true) {
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
    VS("LOADER: Manually flushing stdout and stderr\n");

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
    VS("LOADER: Cleaning up Python interpreter.\n");
    PI_Py_Finalize();
}
