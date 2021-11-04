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
 * Functions to load, initialize and launch Python.
 */
/* size of buffer to store the name of the Python DLL library */
#define DLLNAME_LEN (64)

#ifdef _WIN32
    #include <windows.h> /* HMODULE */
    #include <fcntl.h>   /* O_BINARY */
    #include <io.h>      /* _setmode */
#else
    #include <dlfcn.h>  /* dlerror */
    #include <stdlib.h>  /* mbstowcs */
#endif /* ifdef _WIN32 */
#include <stddef.h>  /* ptrdiff_t */
#include <stdio.h>
#include <string.h>
#include <locale.h>  /* setlocale */

/* PyInstaller headers. */
#include "pyi_pythonlib.h"
#include "pyi_global.h"
#include "pyi_path.h"
#include "pyi_archive.h"
#include "pyi_utils.h"
#include "pyi_python.h"
#include "pyi_win32_utils.h"

/*
 * Load the Python DLL, and get all of the necessary entry points
 */
int
pyi_pylib_load(ARCHIVE_STATUS *status)
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
    if ((p = strrchr(status->cookie.pylibname, '.')) != NULL && strcmp(p, ".a") == 0) {
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
      len = snprintf(dllname, DLLNAME_LEN, "%s", status->cookie.pylibname);
    }
#else
    len = snprintf(dllname, DLLNAME_LEN, "%s", status->cookie.pylibname);
#endif

    if (len >= DLLNAME_LEN) {
        FATALERROR("Reported length (%d) of DLL name (%s) length exceeds buffer[%d] space\n",
                   len, status->cookie.pylibname, DLLNAME_LEN);
        return -1;
    }

#ifdef _WIN32
    /*
     * If ucrtbase.dll exists in temppath, load it proactively before Python
     * library loading to avoid Python library loading failure (unresolved
     * symbol errors) on systems with Universal CRT update not installed.
     */
    if (status->has_temp_directory) {
        char ucrtpath[PATH_MAX];
        if (pyi_path_join(ucrtpath,
                          status->temppath, "ucrtbase.dll") == NULL) {
            FATALERROR("Path of ucrtbase.dll (%s) length exceeds "
                       "buffer[%d] space\n", status->temppath, PATH_MAX);
        };
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
    if (pyi_path_join(dllpath, status->mainpath, dllname) == NULL) {
        FATALERROR("Path of DLL (%s) length exceeds buffer[%d] space\n",
                   status->mainpath, PATH_MAX);
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

    return pyi_python_map_names(dll, pyvers);
}

/*
 * Use this from a dll instead of pyi_pylib_load().
 * It will attach to an existing pythonXX.dll or load one if needed.
 */
int
pyi_pylib_attach(ARCHIVE_STATUS *status, int *loadedNew)
{
#ifdef _WIN32
    HMODULE dll;
    char nm[PATH_MAX + 1];
    int ret = 0;

    /* Get python's name */
    sprintf(nm, "python%d%d.dll", pyvers / 100, pyvers % 100);

    /* See if it's loaded */
    dll = GetModuleHandleA(nm);

    if (dll == 0) {
        *loadedNew = 1;
        return pyi_pylib_load(status);
    }
    ret = pyi_python_map_names(dll, pyvers);
    *loadedNew = 0;
    return ret;
#endif /* ifdef _WIN32 */
    return 0;
}

/*
 * A toc entry of type 'o' holds runtime options
 * toc->name is the arg
 * this is so you can freeze in command line args to Python
 */
static int
pyi_pylib_set_runtime_opts(ARCHIVE_STATUS *status)
{
    int unbuffered = 0;
    TOC *ptoc = status->tocbuff;
    wchar_t wchar_tmp[PATH_MAX + 1];

    /*
     * Startup flags - default values. 1 means enabled, 0 disabled.
     */
    /* Suppress 'import site'. */
    *PI_Py_NoSiteFlag = 1;
    /* Needed by getpath.c from Python. */
    *PI_Py_FrozenFlag = 1;
    /* Suppress writing bytecode files (*.py[co]) */
    *PI_Py_DontWriteBytecodeFlag = 1;
    /* Do not try to find any packages in user's site directory. */
    *PI_Py_NoUserSiteDirectory = 1;
    /* This flag ensures PYTHONPATH and PYTHONHOME are ignored by Python. */
    *PI_Py_IgnoreEnvironmentFlag = 1;
    /* Disable verbose imports by default. */
    *PI_Py_VerboseFlag = 0;

    /* Override some runtime options by custom values from PKG archive.
     * User is allowed to changes these options. */
    for (; ptoc < status->tocend; ptoc = pyi_arch_increment_toc_ptr(status, ptoc)) {
        if (ptoc->typcd == ARCHIVE_ITEM_RUNTIME_OPTION) {
            if (0 == strncmp(ptoc->name, "pyi-", 4)) {
                VS("LOADER: Bootloader option: %s\n", ptoc->name);
                continue;  /* Not handled here - use pyi_arch_get_option(status, ...) */
            }
            VS("LOADER: Runtime option: %s\n", ptoc->name);

            switch (ptoc->name[0]) {
            case 'v':
                *PI_Py_VerboseFlag = 1;
                break;
            case 'u':
                unbuffered = 1;
                break;
            case 'W':
                /* TODO: what encoding is ptoc->name? May not be important */
                /* as all known Wflags are ASCII. */
                if ((size_t)-1 == mbstowcs(wchar_tmp, &ptoc->name[2], PATH_MAX)) {
                    FATALERROR("Failed to convert Wflag %s using mbstowcs "
                               "(invalid multibyte string)\n", &ptoc->name[2]);
                    return -1;
                }
                PI_PySys_AddWarnOption(wchar_tmp);
                break;
            case 'O':
                *PI_Py_OptimizeFlag = 1;
                break;
            }
        }
    }

    if (unbuffered) {
#ifdef _WIN32
        _setmode(fileno(stdin), _O_BINARY);
        _setmode(fileno(stdout), _O_BINARY);
#endif
        fflush(stdout);
        fflush(stderr);

        setbuf(stdin, (char *)NULL);
        setbuf(stdout, (char *)NULL);
        setbuf(stderr, (char *)NULL);

        /* Enable unbuffered mode via Py_UnbufferedStdioFlag */
        *PI_Py_UnbufferedStdioFlag = 1;
    }
    return 0;
}

void
pyi_free_wargv(wchar_t ** wargv)
{
    wchar_t ** arg = wargv;

    while (arg[0]) {
#ifdef _WIN32
        // allocated using `malloc` in pyi_win32_wargv_from_utf8
        free(arg[0]);
#else
        // allocated using Py_DecodeLocale in pyi_wargv_from_argv
        PI_PyMem_RawFree(arg[0]);
#endif
        arg++;
    }
    free(wargv);
}

/* Convert argv to wchar_t for Python 3. Based on code from Python's main().
 *
 * Uses 'Py_DecodeLocale' ('_Py_char2wchar' in 3.0-3.4) function from python lib,
 * so don't call until after python lib is loaded.
 *
 * Returns NULL on failure. Caller is responsible for freeing
 * both argv and argv[0..argc]
 */

wchar_t **
pyi_wargv_from_argv(int argc, char ** argv)
{
    wchar_t ** wargv;
    char *oldloc;
    int i;

    oldloc = strdup(setlocale(LC_CTYPE, NULL));

    if (!oldloc) {
        FATALERROR("out of memory\n");
        return NULL;
    }

    wargv = (wchar_t **)calloc(sizeof(wchar_t*) * (argc + 1), 1);

    if (!wargv) {
        FATALERROR("out of memory\n");
        return NULL;
    }

    setlocale(LC_CTYPE, "");

    for (i = 0; i < argc; i++) {

        wargv[i] = PI_Py_DecodeLocale(argv[i], NULL);

        if (!wargv[i]) {
            pyi_free_wargv(wargv);
            free(oldloc);
            FATALERROR("Fatal error: "
                       "unable to decode the command line argument #%i\n",
                       i + 1);
            return NULL;
        }
    }
    wargv[argc] = NULL;

    setlocale(LC_CTYPE, oldloc);
    free(oldloc);
    return wargv;
}

/*
 * Set Python list sys.argv from *argv/argc. (Command-line options).
 * sys.argv[0] should be full absolute path to the executable (Derived from
 * status->archivename).
 */
static int
pyi_pylib_set_sys_argv(ARCHIVE_STATUS *status)
{
    wchar_t ** wargv;

    VS("LOADER: Setting sys.argv\n");

#ifdef _WIN32
    /* Convert UTF-8 argv back to wargv */
    wargv = pyi_win32_wargv_from_utf8(status->argc, status->argv);
#else
    /* Convert argv to wargv using Python's Py_DecodeLocale */
    wargv = pyi_wargv_from_argv(status->argc, status->argv);
#endif

    if (wargv) {
        /* last parameter '0' to PySys_SetArgv means do not update sys.path. */
        PI_PySys_SetArgvEx(status->argc, wargv, 0);
        pyi_free_wargv(wargv);
    }
    else {
        FATALERROR("Failed to convert argv to wchar_t\n");
        return -1;
    };
    return 0;
}

/* Convenience function to convert current locale to wchar_t on Linux/OS X
 * and convert UTF-8 to wchar_t on Windows.
 *
 * To be called when converting internal PyI strings to wchar_t for
 * Python 3's consumption
 */
wchar_t *
pyi_locale_char2wchar(wchar_t * dst, char * src, size_t len)
{
#ifdef _WIN32
    return pyi_win32_utils_from_utf8(dst, src, len);
#else
    wchar_t * buffer;
    saved_locale = strdup(setlocale(LC_CTYPE, NULL));
    setlocale(LC_CTYPE, "");

    buffer = PI_Py_DecodeLocale(src, &len);

    setlocale(LC_CTYPE, saved_locale);

    if (!buffer) {
        return NULL;
    }
    wcsncpy(dst, buffer, len);
    PI_PyMem_RawFree(buffer);
    return dst;
#endif /* ifdef _WIN32 */
}

/*
 * Start python - return 0 on success
 */
int
pyi_pylib_start_python(ARCHIVE_STATUS *status)
{
    /* Set sys.path, sys.prefix, and sys.executable so dynamic libs will load.
     *
     * The Python APIs we use here (Py_SetProgramName, Py_SetPythonHome)
     * specify their argument should be a "string in static storage".
     * That is, the APIs use the string pointer as given and will neither copy
     * its contents nor free its memory.
     *
     * NOTE: Statics are zero-initialized. */
    #define MAX_PYPATH_SIZE (3 * PATH_MAX + 32)
    static char pypath[MAX_PYPATH_SIZE];

    /* Wide string forms of the above, for Python 3. */
    static wchar_t pypath_w[MAX_PYPATH_SIZE];
    static wchar_t pyhome_w[PATH_MAX + 1];
    static wchar_t progname_w[PATH_MAX + 1];

    /* Decode using current locale */
    if (!pyi_locale_char2wchar(progname_w, status->executablename, PATH_MAX)) {
        FATALERROR("Failed to convert progname to wchar_t\n");
        return -1;
    }
    /* Py_SetProgramName() should be called before Py_SetPath(). */
    PI_Py_SetProgramName(progname_w);

    VS("LOADER: Manipulating environment (sys.path, sys.prefix)\n");

    /* Set sys.prefix and sys.exec_prefix using Py_SetPythonHome */
    /* Decode using current locale */
    if (!pyi_locale_char2wchar(pyhome_w, status->mainpath, PATH_MAX)) {
        FATALERROR("Failed to convert pyhome to wchar_t\n");
        return -1;
    }
    VS("LOADER: sys.prefix is %s\n", status->mainpath);
    PI_Py_SetPythonHome(pyhome_w);

    /* Set sys.path */
    /* sys.path = [mainpath/base_library.zip, mainpath/lib-dynload, mainpath] */
    if (snprintf(pypath, MAX_PYPATH_SIZE, "%s%c%s" "%c" "%s%c%s" "%c" "%s",
                 status->mainpath, PYI_SEP, "base_library.zip",
                 PYI_PATHSEP,
                 status->mainpath, PYI_SEP, "lib-dynload",
                 PYI_PATHSEP,
                 status->mainpath)
        >= MAX_PYPATH_SIZE) {
        // This should never happen, since mainpath is < PATH_MAX and pypath is
        // huge enough
        FATALERROR("sys.path (based on %s) exceeds buffer[%d] space\n",
                   status->mainpath, MAX_PYPATH_SIZE);
        return -1;
    }

    /*
     * We must set sys.path to have base_library.zip before
     * calling Py_Initialize as it needs `encodings` and other modules.
     */
    /* Decode using current locale */
    if (!pyi_locale_char2wchar(pypath_w, pypath, MAX_PYPATH_SIZE)) {
        FATALERROR("Failed to convert pypath to wchar_t\n");
        return -1;
    }
    VS("LOADER: Pre-init sys.path is %s\n", pypath);
#ifdef _WIN32
    // Call GetPath first, so the static dllpath will be set as a side
    // effect. Workaround for http://bugs.python.org/issue29778, see #2496.
    // Due to another bug calling this on non-win32 with Python 3.6 causes
    // memory corruption, see #2812 and
    // https://bugs.python.org/issue31532. But the workaround is only
    // needed for win32.
    PI_Py_GetPath();
#endif
    PI_Py_SetPath(pypath_w);

    /* Start python. */
    VS("LOADER: Setting runtime options\n");
    pyi_pylib_set_runtime_opts(status);

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

    VS("LOADER: Initializing python\n");
    PI_Py_Initialize();

#if defined(_WIN32) && defined(LAUNCH_DEBUG)
    SetErrorMode(0);
#endif

    /*
     * Set sys.path list.
     * Python's default sys.path is no good - it includes the working directory
     * and the folder containing the executable. Replace sys.path with only
     * the paths we want.
     */
    VS("LOADER: Overriding Python's sys.path\n");
    VS("LOADER: Post-init sys.path is %s\n", pypath);
    PI_PySys_SetPath(pypath_w);

    /* Setting sys.argv should be after Py_Initialize() call. */
    if (pyi_pylib_set_sys_argv(status)) {
        return -1;
    }

    /* Check for a python error */
    if (PI_PyErr_Occurred()) {
        FATALERROR("Error detected starting Python VM.\n");
        return -1;
    }

    return 0;
}

/*
 * Import modules embedded in the archive - return 0 on success
 */
int
pyi_pylib_import_modules(ARCHIVE_STATUS *status)
{
    TOC *ptoc;
    PyObject *co;
    PyObject *mod;
    PyObject *meipass_obj;

    VS("LOADER: setting sys._MEIPASS\n");

    /* TODO extract function pyi_char_to_pyobject */
#ifdef _WIN32
    meipass_obj = PI_PyUnicode_Decode(status->mainpath,
                                      strlen(status->mainpath),
                                      "utf-8",
                                      "strict");
#else
    meipass_obj = PI_PyUnicode_DecodeFSDefault(status->mainpath);
#endif

    if (!meipass_obj) {
        FATALERROR("Failed to get _MEIPASS as PyObject.\n");
        return -1;
    }

    PI_PySys_SetObject("_MEIPASS", meipass_obj);

    VS("LOADER: importing modules from CArchive\n");

    /* Iterate through toc looking for module entries (type 'm')
     * this is normally just bootstrap stuff (archive and iu)
     */
    ptoc = status->tocbuff;

    while (ptoc < status->tocend) {
        if (ptoc->typcd == ARCHIVE_ITEM_PYMODULE ||
            ptoc->typcd == ARCHIVE_ITEM_PYPACKAGE) {
            unsigned char *modbuf = pyi_arch_extract(status, ptoc);

            VS("LOADER: extracted %s\n", ptoc->name);

            /* Unmarshall code object for module; we need to skip
               the pyc header */
            if (pyvers >= 307) {
                /* Python 3.7 changed header size to 16 bytes */
                co = PI_PyMarshal_ReadObjectFromString((const char *) modbuf + 16, ptoc->ulen - 16);
            } else {
                co = PI_PyMarshal_ReadObjectFromString((const char *) modbuf + 12, ptoc->ulen - 12);
            }

            if (co != NULL) {
                VS("LOADER: running unmarshalled code object for %s...\n", ptoc->name);
                mod = PI_PyImport_ExecCodeModule(ptoc->name, co);
            }
            else {
                VS("LOADER: failed to unmarshall code object for %s!\n", ptoc->name);
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
        }
        ptoc = pyi_arch_increment_toc_ptr(status, ptoc);
    }

    return 0;
}

/*
 * Install a zlib from a toc entry.
 *
 * Must be called after Py_Initialize (i.e. after pyi_pylib_start_python)
 *
 * The installation is done by adding an entry like
 *    absolute_path/dist/hello_world/hello_world?123456
 * to sys.path. The end number is the offset where the
 * Python bootstrap code should read the zip data.
 * Return non zero on failure.
 * NB: This entry is removed from sys.path by the bootstrap scripts.
 */
int
pyi_pylib_install_zlib(ARCHIVE_STATUS *status, TOC *ptoc)
{
    int rc = 0;
    uint64_t zlibpos = status->pkgstart + ptoc->pos;
    PyObject * sys_path, *zlib_entry, *archivename_obj;

    /* Note that sys.path contains PyUnicode on py3. Ensure
     * that filenames are encoded or decoded correctly.
     */
#ifdef _WIN32
    /* Decode UTF-8 to PyUnicode */
    archivename_obj = PI_PyUnicode_Decode(status->archivename,
                                          strlen(status->archivename),
                                          "utf-8",
                                          "strict");
#else
    /* Decode locale-encoded filename to PyUnicode object using Python's
     * preferred decoding method for filenames.
     */
    archivename_obj = PI_PyUnicode_DecodeFSDefault(status->archivename);
#endif
    zlib_entry = PI_PyUnicode_FromFormat("%U?%" PRIu64, archivename_obj, zlibpos);
    PI_Py_DecRef(archivename_obj);

    sys_path = PI_PySys_GetObject("path");

    if (NULL == sys_path) {
        FATALERROR("Installing PYZ: Could not get sys.path\n");
        PI_Py_DecRef(zlib_entry);
        return -1;
    }

    rc = PI_PyList_Append(sys_path, zlib_entry);

    if (rc) {
        FATALERROR("Failed to append to sys.path\n");
    }

    return rc;
}

/*
 * Install PYZ
 * Return non zero on failure
 */
int
pyi_pylib_install_zlibs(ARCHIVE_STATUS *status)
{
    TOC * ptoc;

    VS("LOADER: Installing PYZ archive with Python modules.\n");

    /* Iterate through toc looking for zlibs (PYZ, type 'z') */
    ptoc = status->tocbuff;

    while (ptoc < status->tocend) {
        if (ptoc->typcd == ARCHIVE_ITEM_PYZ) {
            VS("LOADER: PYZ archive: %s\n", ptoc->name);
            pyi_pylib_install_zlib(status, ptoc);
        }

        ptoc = pyi_arch_increment_toc_ptr(status, ptoc);
    }
    return 0;
}

void
pyi_pylib_finalize(ARCHIVE_STATUS *status)
{
    /*
     * Call this function only if Python library was initialized.
     *
     * Otherwise it should be NULL pointer. If Python library is not properly
     * loaded then calling this function might cause some segmentation faults.
     */
    if (status->is_pylib_loaded == true) {
        #ifndef WINDOWED
            /*
             * We need to manually flush the buffers because otherwise there can be errors.
             * The native python interpreter flushes buffers before calling Py_Finalize,
             * so we need to manually do the same. See isse #4908.
             */

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

        /* Finalize the interpreter. This function call calls all of the atexit functions. */
        VS("LOADER: Cleaning up Python interpreter.\n");
        PI_Py_Finalize();
    }
}
