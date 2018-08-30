/*
 * ****************************************************************************
 * Copyright (c) 2013-2018, PyInstaller Development Team.
 * Distributed under the terms of the GNU General Public License with exception
 * for distributing bootloader.
 *
 * The full license is in the file COPYING.txt, distributed with this software.
 * ****************************************************************************
 */

/*
 * Functions to load, initialize and launch Python.
 */

/* TODO: use safe string functions */
#define _CRT_SECURE_NO_WARNINGS 1

#ifdef _WIN32
    #include <windows.h> /* HMODULE */
    #include <fcntl.h>   /* O_BINARY */
    #include <io.h>      /* _setmode */
    #include <winsock.h> /* ntohl */
#else
    #include <dlfcn.h>  /* dlerror */
    #include <limits.h> /* PATH_MAX */
    #ifdef __FreeBSD__
/* freebsd issue #188316 */
        #include <arpa/inet.h>  /* ntohl */
    #else
        #include <netinet/in.h>  /* ntohl */
    #endif
    #include <stdlib.h>  /* mbstowcs */
#endif /* ifdef _WIN32 */
#include <stddef.h>  /* ptrdiff_t */
#include <stdio.h>
#include <string.h>
#include <locale.h>  /* setlocale */

/* PyInstaller headers. */
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
    char dllname[64];
    char *p;
    int len;

    /* Are we going to load the Python 2.x library? */
    is_py2 = (pyvers / 10) == 2;

/*
 * On AIX Append the shared object member to the library path
 * to make it look like this:
 *   libpython2.6.a(libpython2.6.so)
 */
#ifdef AIX
    /*
     * Determine if shared lib is in libpython?.?.so or libpython?.?.a(libpython?.?.so) format
     */
    if ((p = strrchr(status->cookie.pylibname, '.')) != NULL && strcmp(p, ".a") == 0) {
      /*
       * On AIX 'ar' archives are used for both static and shared object.
       * To load a shared object from a library, it should be loaded like this:
       *   dlopen("libpython2.6.a(libpython2.6.so)", RTLD_MEMBER)
       */
      uint32_t pyvers_major;
      uint32_t pyvers_minor;

      pyvers_major = pyvers / 10;
      pyvers_minor = pyvers % 10;

      len = snprintf(dllname, 64,
              "libpython%01d.%01d.a(libpython%01d.%01d.so)",
              pyvers_major, pyvers_minor, pyvers_major, pyvers_minor);
    }
    else {
      strncpy(dllname, status->cookie.pylibname, 64);
    }
#else
    len = 0;
    strncpy(dllname, status->cookie.pylibname, 64);
#endif

    if (len >= 64 || dllname[64-1] != '\0') {
        FATALERROR("DLL name length exceeds buffer\n");
        return -1;
    }

    /*
     * Look for Python library in homepath or temppath.
     * It depends on the value of mainpath.
     */
    pyi_path_join(dllpath, status->mainpath, dllname);

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
    sprintf(nm, "python%02d.dll", pyvers);

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
    /* Disalbe verbose imports by default. */
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

                if (is_py2) {
                    PI_Py2Sys_AddWarnOption(&ptoc->name[2]);
                }
                else {
                    /* TODO: what encoding is ptoc->name? May not be important */
                    /* as all known Wflags are ASCII. */
                    if ((size_t)-1 == mbstowcs(wchar_tmp, &ptoc->name[2], PATH_MAX)) {
                        FATALERROR("Failed to convert Wflag %s using mbstowcs "
                                   "(invalid multibyte string)\n", &ptoc->name[2]);
                        return -1;
                    }
                    PI_PySys_AddWarnOption(wchar_tmp);
                };
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
    }
    return 0;
}

void
pyi_free_wargv(wchar_t ** wargv)
{
    wchar_t ** arg = wargv;

    while (arg[0]) {
        free(arg[0]);
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
    char ** mbcs_argv;
    wchar_t ** wargv;

    VS("LOADER: Setting sys.argv\n");

    /* last parameter '0' to PySys_SetArgv means do not update sys.path. */
    if (is_py2) {
#ifdef _WIN32
        /*
         * status->argv is UTF-8, convert to ANSI without SFN
         * TODO: pyi-option to enable SFNs for argv?
         */
        mbcs_argv = pyi_win32_argv_mbcs_from_utf8(status->argc, status->argv);

        if (mbcs_argv) {
            PI_Py2Sys_SetArgvEx(status->argc, mbcs_argv, 0);
            free(mbcs_argv);
        }
        else {
            FATALERROR("Failed to convert argv to mbcs\n");
            return -1;
        }
#else   /* _WIN32 */
       /* For Python2, status->argv must be "char **". In Python 2.7's */
       /* `main.c`, argv is used without any other handling, so do we. */
        PI_Py2Sys_SetArgvEx(status->argc, status->argv, 0);
#endif /* ifdef _WIN32 */

    }
    else {
#ifdef _WIN32
        /* Convert UTF-8 argv back to wargv */
        wargv = pyi_win32_wargv_from_utf8(status->argc, status->argv);
#else
        /* Convert argv to wargv using Python's Py_DecodeLocale (formerly _Py_char2wchar) */
        wargv = pyi_wargv_from_argv(status->argc, status->argv);
#endif

        if (wargv) {
            PI_PySys_SetArgvEx(status->argc, wargv, 0);
            pyi_free_wargv(wargv);
        }
        else {
            FATALERROR("Failed to convert argv to wchar_t\n");
            return -1;
        }
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
    free(buffer);
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
    static char pypath[2 * PATH_MAX + 14];
    static char pypath_sfn[2 * PATH_MAX + 14];
    static char pyhome[PATH_MAX + 1];
    static char progname[PATH_MAX + 1];

    /* Wide string forms of the above, for Python 3. */
    static wchar_t pypath_w[PATH_MAX + 1];
    static wchar_t pyhome_w[PATH_MAX + 1];
    static wchar_t progname_w[PATH_MAX + 1];

    if (is_py2) {
#ifdef _WIN32

        /* Use ShortFileName - affects sys.executable */
        if (!pyi_win32_utf8_to_mbs_sfn(progname, status->archivename, PATH_MAX)) {
            FATALERROR("Failed to convert progname to wchar_t\n");
            return -1;
        }
#else
        /* Use system-provided filename. No encoding. */
        strncpy(progname, status->archivename, PATH_MAX);
#endif
        PI_Py2_SetProgramName(progname);
    }
    else {
        /* Decode using current locale */
        if (!pyi_locale_char2wchar(progname_w, status->archivename, PATH_MAX)) {
            FATALERROR("Failed to convert progname to wchar_t\n");
            return -1;
        }
        /* In Python 3 Py_SetProgramName() should be called before Py_SetPath(). */
        PI_Py_SetProgramName(progname_w);
    };

    VS("LOADER: Manipulating environment (sys.path, sys.prefix)\n");

    /* Set sys.prefix and sys.exec_prefix using Py_SetPythonHome */
    if (is_py2) {
#ifdef _WIN32

        if (!pyi_win32_utf8_to_mbs_sfn(pyhome, status->mainpath, PATH_MAX)) {
            FATALERROR("Failed to convert pyhome to ANSI (invalid multibyte string)\n");
            return -1;
        }
#else
        strcpy(pyhome, status->mainpath);
#endif
        VS("LOADER: sys.prefix is %s\n", pyhome);
        PI_Py2_SetPythonHome(pyhome);
    }
    else {
        /* Decode using current locale */
        if (!pyi_locale_char2wchar(pyhome_w, status->mainpath, PATH_MAX)) {
            FATALERROR("Failed to convert pyhome to wchar_t\n");
            return -1;
        }
        VS("LOADER: sys.prefix is %s\n", status->mainpath);
        PI_Py_SetPythonHome(pyhome_w);
    };

    /* Set sys.path */
    if (is_py2) {
        /* sys.path = [mainpath] */
        strncpy(pypath, status->mainpath, strlen(status->mainpath));
    }
    else {
        /* sys.path = [base_library, mainpath] */
        strncpy(pypath, status->mainpath, strlen(status->mainpath));
        strncat(pypath, PYI_SEPSTR, strlen(PYI_SEPSTR));
        strncat(pypath, "base_library.zip", strlen("base_library.zip"));
        strncat(pypath, PYI_PATHSEPSTR, strlen(PYI_PATHSEPSTR));
        strncat(pypath, status->mainpath, strlen(status->mainpath));
    };

    /*
     * On Python 3, we must set sys.path to have base_library.zip before
     * calling Py_Initialize as it needs `encodings` and other modules.
     */
    if (!is_py2) {
        /* Decode using current locale */
        if (!pyi_locale_char2wchar(pypath_w, pypath, PATH_MAX)) {
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
    }
    ;

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

    if (is_py2) {
#ifdef _WIN32

        if (!pyi_win32_utf8_to_mbs_sfn(pypath_sfn, pypath, PATH_MAX)) {
            FATALERROR("Failed to convert pypath to ANSI (invalid multibyte string)\n");
        }
        PI_Py2Sys_SetPath(pypath_sfn);
#else
        PI_Py2Sys_SetPath(pypath);
#endif
    }
    else {
        PI_PySys_SetPath(pypath_w);
    };

    /* Setting sys.argv should be after Py_Initialize() call. */
    if (pyi_pylib_set_sys_argv(status)) {
        return -1;
    }

    /* Check for a python error */
    if (PI_PyErr_Occurred()) {
        FATALERROR("Error detected starting Python VM.");
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
    PyObject *marshal;
    PyObject *marshaldict;
    PyObject *loadfunc;
    TOC *ptoc;
    PyObject *co;
    PyObject *mod;
    PyObject *meipass_obj;
    char * meipass_ansi;

    VS("LOADER: setting sys._MEIPASS\n");

    /* TODO extract function pyi_char_to_pyobject */
    if (is_py2) {
#ifdef _WIN32
        meipass_ansi = pyi_win32_utf8_to_mbs_sfn(NULL, status->mainpath, 0);

        if (!meipass_ansi) {
            FATALERROR("Failed to encode _MEIPASS as ANSI.\n");
            return -1;
        }
        meipass_obj = PI_PyString_FromString(meipass_ansi);
        free(meipass_ansi);
#else
        meipass_obj = PI_PyString_FromString(status->mainpath);
#endif
    }
    else {
#ifdef _WIN32
        meipass_obj = PI_PyUnicode_Decode(status->mainpath,
                                          strlen(status->mainpath),
                                          "utf-8",
                                          "strict");
#else
        meipass_obj = PI_PyUnicode_DecodeFSDefault(status->mainpath);
#endif
    }

    if (!meipass_obj) {
        FATALERROR("Failed to get _MEIPASS as PyObject.\n");
        return -1;
    }

    PI_PySys_SetObject("_MEIPASS", meipass_obj);

    VS("LOADER: importing modules from CArchive\n");

    /* Get the Python function marshall.load
     * Here we collect some reference to PyObject that we don't dereference
     * Doesn't matter because the objects won't be going away anyway.
     */
    marshal = PI_PyImport_ImportModule("marshal");
    marshaldict = PI_PyModule_GetDict(marshal);
    loadfunc = PI_PyDict_GetItemString(marshaldict, "loads");

    /* Iterate through toc looking for module entries (type 'm')
     * this is normally just bootstrap stuff (archive and iu)
     */
    ptoc = status->tocbuff;

    while (ptoc < status->tocend) {
        if (ptoc->typcd == ARCHIVE_ITEM_PYMODULE ||
            ptoc->typcd == ARCHIVE_ITEM_PYPACKAGE) {
            unsigned char *modbuf = pyi_arch_extract(status, ptoc);

            VS("LOADER: extracted %s\n", ptoc->name);

            /* .pyc/.pyo files have 8 bytes header. Skip it and load marshalled
             * data form the right point.
             */
            if (is_py2) {
                co = PI_PyObject_CallFunction(loadfunc, "s#", modbuf + 8, ntohl(
                                                  ptoc->ulen) - 8);
            }
            else if (pyvers >= 37) {
                /* Python >= 3.7 the header: size was changed to 16 bytes. */
                co = PI_PyObject_CallFunction(loadfunc, "y#", modbuf + 16,
                                              ntohl(ptoc->ulen) - 16);
            }
            else {
                /* It looks like from python 3.3 the header */
                /* size was changed to 12 bytes. */
                co =
                    PI_PyObject_CallFunction(loadfunc, "y#", modbuf + 12, ntohl(
                                                 ptoc->ulen) - 12);
            };

            if (co != NULL) {
                VS("LOADER: callfunction returned...\n");
                mod = PI_PyImport_ExecCodeModule(ptoc->name, co);
            }
            else {
                /* TODO callfunctions might return NULL - find yout why and foor what modules. */
                VS("LOADER: callfunction returned NULL");
                mod = NULL;
            }

            /* Check for errors in loading */
            if (mod == NULL) {
                FATALERROR("mod is NULL - %s", ptoc->name);
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
    int zlibpos = status->pkgstart + ntohl(ptoc->pos);
    PyObject * sys_path, *zlib_entry, *archivename_obj;
    char *archivename;

    /* Note that sys.path contains PyString on py2, and PyUnicode on py3. Ensure
     * that filenames are encoded or decoded correctly.
     */
    if (is_py2) {
#ifdef _WIN32
        /* Must be MBCS encoded. Use SFN if possible.
         *
         * We could instead pass the UTF-8 encoded form and modify FrozenImporter to
         * decode it on Windows, but this breaks the convention that `sys.path`
         * entries on Windows are MBCS encoded, and may interfere with any code
         * that inspects `sys.path`
         *
         * We could also pass the zlib path through a channel other than `sys.path`
         * to sidestep that requirement, but there's not much benefit as this only
         * improves non-codepage/non-SFN compatibility for the zlib and not any other
         * importable modules.
         */

        archivename = pyi_win32_utf8_to_mbs_sfn(NULL, status->archivename, 0);

        if (NULL == archivename) {
            FATALERROR("Failed to convert %s to ShortFileName\n", status->archivename);
            return -1;
        }
#else
        /* Use system-provided path. No encoding required. */
        archivename = status->archivename;
#endif
        zlib_entry = PI_PyString_FromFormat("%s?%d", archivename, zlibpos);

        if (archivename != status->archivename) {
            free(archivename);
        }

    }
    else {
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
        zlib_entry = PI_PyUnicode_FromFormat("%U?%d", archivename_obj, zlibpos);
        PI_Py_DecRef(archivename_obj);
    }

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
        VS("LOADER: Cleaning up Python interpreter.\n");
        PI_Py_Finalize();
    }
}
