/*
 * ****************************************************************************
 * Copyright (c) 2023, PyInstaller Development Team.
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
 * Functions to deal with PEP 587 python initialization configuration.
 */

#include <stdlib.h>
#include <string.h>

#include "pyi_pyconfig.h"
#include "pyi_global.h"
#include "pyi_utils.h"
#include "pyi_win32_utils.h"


/*
 * Clean up and free the PyiRuntimeOptions structure created by
 * pyi_config_parse_runtime_options(). No-op if passed a NULL pointer.
 */
void
pyi_runtime_options_free(PyiRuntimeOptions *options)
{
    if (options == NULL) {
        return;
    }

    /* Free the wflags array */
    if (options->num_wflags) {
        int i;
        for (i = 0; i < options->num_wflags; i++) {
            free(options->wflags[i]);
        }
    }
    free(options->wflags);

    /* Free options structure itself */
    free(options);
}

/*
 * Allocate the PyiRuntimeOptions structure and populate it based on
 * options found in the PKG archive.
 */
PyiRuntimeOptions *
pyi_runtime_options_read(const ARCHIVE_STATUS *archive_status)
{
    PyiRuntimeOptions *options;
    TOC *ptoc;
    int num_wflags = 0;
    int failed = 0;
    char *env_utf8 = NULL;

    /* Allocate the structure */
    options = calloc(1, sizeof(PyiRuntimeOptions));
    if (options == NULL) {
        return options;
    }

    /* Honor the setting via PYTHONUTF8 environment variable (valid
     * values are 0 and 1, same as with python interpreter) */
    /* TODO: replace this with -Xutf8=0 / -Xutf8=1 bootloader option
     * and ignore the environment */
    options->utf8_mode = -1; /* Auto-select by default */
    env_utf8 = pyi_getenv("PYTHONUTF8");
    if (env_utf8) {
        if (strcmp(env_utf8, "0") == 0) {
            options->utf8_mode = 0;
        } else if (strcmp(env_utf8, "1") == 0) {
            options->utf8_mode = 1;
        } else {
            OTHERERROR("Invalid value for PYTHONUTF8=%s; disabling utf-8 mode!\n", env_utf8);
            options->utf8_mode = 0;
        }
    }

    /* Parse run-time options from PKG archive */
    for (ptoc = archive_status->tocbuff; ptoc < archive_status->tocend; ptoc = pyi_arch_increment_toc_ptr(archive_status, ptoc)) {
        /* Skip bootloader options; these start with "pyi-" */
        if (strncmp(ptoc->name, "pyi-", 4) == 0) {
            continue;
        }

        /* Verbose flag: v, verbose */
        if (strcmp(ptoc->name, "v") == 0 || strcmp(ptoc->name, "verbose") == 0) {
            options->verbose++;
            continue;
        }

        /* Unbuffered flag: u, unbuffered */
        if (strcmp(ptoc->name, "u") == 0 || strcmp(ptoc->name, "unbuffered") == 0) {
            options->unbuffered = 1;
            continue;
        }

        /* Optimize flag: O, optimize */
        if (strcmp(ptoc->name, "O") == 0 || strcmp(ptoc->name, "optimize") == 0) {
            options->optimize++;
            continue;
        }

        /* W flag */
        if (ptoc->name[0] == 'W') {
            num_wflags++;
            continue;
        }
    }

    if (num_wflags) {
        /* Allocate Wflags array */
        options->wflags = calloc(num_wflags, sizeof(wchar_t *));
        if (options->wflags == NULL) {
            failed = 1;
            goto end;
        }

        /* Collect Wflags */
        for (ptoc = archive_status->tocbuff; ptoc < archive_status->tocend; ptoc = pyi_arch_increment_toc_ptr(archive_status, ptoc)) {
            if (ptoc->name[0] != 'W') {
                continue;
            }

            /* Convert multi-byte string to wide-char. The multibyte
             * encoding should be UTF-8, although W-options should
             * consist only of ASCII characters. */
            wchar_t wflag_tmp[PATH_MAX];
            if (mbstowcs(wflag_tmp, &ptoc->name[2], PATH_MAX) == -1) {
                failed = 1;
                goto end;
            }

            /* Copy */
            options->wflags[options->num_wflags] = wcsdup(wflag_tmp);
            if (options->wflags[options->num_wflags] == NULL) {
                failed = 1;
                goto end;
            }
            options->num_wflags++;
        }
    }

end:
    /* Clean-up on error */
    if (failed) {
        pyi_runtime_options_free(options);
        options = NULL;
    }

    return options;
}


/*
 * Helper that sets a string field in the PyConfig structure.
 * On Windows, the string is converted from UTF-8 to wide-character, and
 * set using PyConfig_SetString. On other systems, PyConfig_SetBytesString
 * is used, which internally calls Py_DecodeLocale.
 */
static int
_pyi_pyconfig_set_string(PyConfig *config, wchar_t **dest_field, const char *str)
{
    PyStatus status;

#ifdef _WIN32
    wchar_t *str_w;
    str_w = pyi_win32_utils_from_utf8(NULL, str, 0);
    if (!str_w) {
        return -1;
    }
    status = PI_PyConfig_SetString(config, dest_field, str_w);
    free(str_w);
#else
    status = PI_PyConfig_SetBytesString(config, dest_field, str);
#endif

    return PI_PyStatus_Exception(status) ? -1 : 0;
}


/*
 * Allocate the PyConfig structure, based on the python version.
 */
PyConfig *
pyi_pyconfig_create()
{
    /* Macro to avoid manual code repetition. */
    #define _IMPL_CASE(PY_VERSION, PYCONFIG_IMPL) \
    case PY_VERSION: { \
        return (PyConfig *)calloc(1, sizeof(PYCONFIG_IMPL)); \
    }
    /* Macro end */

    switch (pyvers) {
        _IMPL_CASE(308, PyConfig_v38)
        _IMPL_CASE(309, PyConfig_v39)
        _IMPL_CASE(310, PyConfig_v310)
        _IMPL_CASE(311, PyConfig_v311)
        _IMPL_CASE(312, PyConfig_v312)
        default: {
            break;
        }
    }

    #undef _IMPL_CASE

    return NULL; /* Unsupported python version */
}

/*
 * Clean up and free the PyConfig structure.
 */
void
pyi_pyconfig_free(PyConfig *config)
{
    /* Clear the fields that PyConfig API allocated */
    PI_PyConfig_Clear(config);

    /* Free the allocated structure itself; was allocated using calloc
     * in pyi_pyconfig_create(). */
    free(config);
}

/*
 * Set program name. Used to set sys.executable, and in early error messages.
 */
int
pyi_pyconfig_set_program_name(PyConfig *config, const ARCHIVE_STATUS *archive_status)
{
    /* Macro to avoid manual code repetition. */
    #define _IMPL_CASE(PY_VERSION, PYCONFIG_IMPL) \
    case PY_VERSION: { \
        PYCONFIG_IMPL *config_impl = (PYCONFIG_IMPL *)config; \
        if (_pyi_pyconfig_set_string(config, &config_impl->program_name, archive_status->executablename) < 0) { \
            return -1; \
        } \
        return 0; \
    }
    /* Macro end */

    switch (pyvers) {
        _IMPL_CASE(308, PyConfig_v38)
        _IMPL_CASE(309, PyConfig_v39)
        _IMPL_CASE(310, PyConfig_v310)
        _IMPL_CASE(311, PyConfig_v311)
        _IMPL_CASE(312, PyConfig_v312)
        default: {
            break;
        }
    }

    #undef _IMPL_CASE

    return -1; /* Unsupported python version */
}

/*
 * Set python home directory. Used to set sys.prefix.
 */
int
pyi_pyconfig_set_python_home(PyConfig *config, const ARCHIVE_STATUS *archive_status)
{
    /* Macro to avoid manual code repetition. */
    #define _IMPL_CASE(PY_VERSION, PYCONFIG_IMPL) \
    case PY_VERSION: { \
        PYCONFIG_IMPL *config_impl = (PYCONFIG_IMPL *)config; \
        return _pyi_pyconfig_set_string(config, &config_impl->home, archive_status->mainpath); \
    }
    /* Macro end */

    switch (pyvers) {
        _IMPL_CASE(308, PyConfig_v38)
        _IMPL_CASE(309, PyConfig_v39)
        _IMPL_CASE(310, PyConfig_v310)
        _IMPL_CASE(311, PyConfig_v311)
        _IMPL_CASE(312, PyConfig_v312)
        default: {
            break;
        }
    }

    #undef _IMPL_CASE

    return -1; /* Unsupported python version */
}

/*
 * Set module search paths (sys.path).
 *
 * Setting `pythonpath_env` seems to not have the desired effect (python
 * overrides sys.path with pre-defined paths anchored in home directory).
 * Therefore, we directly manipulate the `module_search_paths` and
 * `module_search_paths_set`, which puts the desired set of paths into
 * sys.path.
 */
static int
_pyi_pyconfig_set_module_search_paths(PyConfig *config, int num_paths, wchar_t **paths)
{
    /* Macro to avoid manual code repetition. */
    #define _IMPL_CASE(PY_VERSION, PYCONFIG_IMPL) \
    case PY_VERSION: { \
        PyStatus status; \
        PYCONFIG_IMPL *config_impl = (PYCONFIG_IMPL *)config; \
        status = PI_PyConfig_SetWideStringList(config, &config_impl->module_search_paths, num_paths, paths); \
        config_impl->module_search_paths_set = 1; \
        return PI_PyStatus_Exception(status) ? -1 : 0; \
    }
    /* Macro end */

    switch (pyvers) {
        _IMPL_CASE(308, PyConfig_v38)
        _IMPL_CASE(309, PyConfig_v39)
        _IMPL_CASE(310, PyConfig_v310)
        _IMPL_CASE(311, PyConfig_v311)
        _IMPL_CASE(312, PyConfig_v312)
        default: {
            break;
        }
    }

    #undef _IMPL_CASE

    return -1; /* Unsupported python version */
}

int
pyi_pyconfig_set_module_search_paths(PyConfig *config, const ARCHIVE_STATUS *archive_status)
{
    /* TODO: instead of stitching together char strings and converting
     * them, we could probably stitch together wide-char strings directly,
     * as `home` field in config structure has already been converted. */
    char base_library_path[PATH_MAX + 1];
    char lib_dynload_path[PATH_MAX + 1];

    const char *module_search_paths[3];
    wchar_t *module_search_paths_w[3];

    int ret = 0;
    int i;

    /* home/base_library.zip */
    if (snprintf(base_library_path, PATH_MAX, "%s%c%s", archive_status->mainpath, PYI_SEP, "base_library.zip") >= PATH_MAX) {
        return -1;
    }

    /* home/lib-dynload */
    if (snprintf(lib_dynload_path, PATH_MAX, "%s%c%s", archive_status->mainpath, PYI_SEP, "lib-dynload") >= PATH_MAX) {
        return -1;
    }

    module_search_paths[0] = base_library_path;
    module_search_paths[1] = lib_dynload_path;
    module_search_paths[2] = archive_status->mainpath;

    /* Convert */
    for (i = 0; i < 3; i++) {
#ifdef _WIN32
        module_search_paths_w[i] = pyi_win32_utils_from_utf8(NULL, module_search_paths[i], 0);
#else
        module_search_paths_w[i] = PI_Py_DecodeLocale(module_search_paths[i], NULL);
#endif
        if (module_search_paths_w[i] == NULL) {
            /* Do not break; we need to initialize all elements */
            ret = -1;
        }
    }
    if (ret < -1) {
        goto end; /* Conversion of at least one path failed */
    }

    /* Set */
    ret = _pyi_pyconfig_set_module_search_paths(config, 3, module_search_paths_w);

end:
    /* Cleanup */
    for (i = 0; i < 3; i++) {
#ifdef _WIN32
        free(module_search_paths_w[i]);
#else
        PI_PyMem_RawFree(module_search_paths_w[i]);
#endif
    }

    return ret;
}


/*
 * Set program arguments (sys.argv).
 */
static int
_pyi_pyconfig_set_argv(PyConfig *config, int argc, wchar_t **argv_w)
{
    /* Macro to avoid manual code repetition. */
    #define _IMPL_CASE(PY_VERSION, PYCONFIG_IMPL) \
    case PY_VERSION: { \
        PyStatus status; \
        PYCONFIG_IMPL *config_impl = (PYCONFIG_IMPL *)config; \
        status = PI_PyConfig_SetWideStringList(config, &config_impl->argv, argc, argv_w); \
        return PI_PyStatus_Exception(status) ? -1 : 0; \
    }
    /* Macro end */

    switch (pyvers) {
        _IMPL_CASE(308, PyConfig_v38)
        _IMPL_CASE(309, PyConfig_v39)
        _IMPL_CASE(310, PyConfig_v310)
        _IMPL_CASE(311, PyConfig_v311)
        _IMPL_CASE(312, PyConfig_v312)
        default: {
            break;
        }
    }

    #undef _IMPL_CASE

    return -1; /* Unsupported python version */
}


int
pyi_pyconfig_set_argv(PyConfig *config, const ARCHIVE_STATUS *archive_status)
{
    wchar_t **argv_w;
    int ret = 0;
    int i;

    /* Allocate */
    argv_w = calloc(archive_status->argc, sizeof(wchar_t *));
    if (argv_w == NULL) {
        return -1;
    }

    /* Convert */
    for (i = 0; i < archive_status->argc; i++) {
#ifdef _WIN32
        argv_w[i] = pyi_win32_utils_from_utf8(NULL, archive_status->argv[i], 0);
#else
        argv_w[i] = PI_Py_DecodeLocale(archive_status->argv[i], NULL);
#endif
        if (argv_w[i] == NULL) {
            /* Do not break; we need to initialize all elements */
            ret = -1;
        }
    }
    if (ret < -1) {
        goto end; /* Conversion of at least one arg failed */
    }

    /* Set */
    ret = _pyi_pyconfig_set_argv(config, archive_status->argc, argv_w);

end:
    /* Cleanup */
    for (i = 0; i < archive_status->argc; i++) {
#ifdef _WIN32
        free(argv_w[i]);
#else
        PI_PyMem_RawFree(argv_w[i]);
#endif
    }
    free(argv_w);

    return ret;
}


/*
 * Set run-time options.
 */
int
pyi_pyconfig_set_runtime_options(PyConfig *config, const PyiRuntimeOptions *runtime_options)
{
    /* Macro to avoid manual code repetition. */
    #define _IMPL_CASE(PY_VERSION, PYCONFIG_IMPL) \
    case PY_VERSION: { \
        PyStatus status; \
        PYCONFIG_IMPL *config_impl = (PYCONFIG_IMPL *)config; \
        /* Extend the isolated config, which leaves site_import and write_bytecode on */ \
        config_impl->site_import = 0; \
        config_impl->write_bytecode = 0; \
        /* Enable configure_c_stdio (disabled in isolated config by default) to let python configure stdout/stderr
         * streams (set binary mode, disable buffer in unbuffered mode, etc.) */ \
        config_impl->configure_c_stdio = 1; \
        /* These flags map to our run-time options (O, u, v) */ \
        config_impl->optimization_level = runtime_options->optimize; \
        config_impl->buffered_stdio = !runtime_options->unbuffered; \
        config_impl->verbose = runtime_options->verbose; \
        /* Set W-flags, if available */ \
        if (runtime_options->num_wflags) { \
            status = PI_PyConfig_SetWideStringList(config, &config_impl->warnoptions, runtime_options->num_wflags, runtime_options->wflags); \
            if (PI_PyStatus_Exception(status)) { \
                return -1; \
            } \
        } \
        return 0; \
    }
    /* Macro end */

    switch (pyvers) {
        _IMPL_CASE(308, PyConfig_v38)
        _IMPL_CASE(309, PyConfig_v39)
        _IMPL_CASE(310, PyConfig_v310)
        _IMPL_CASE(311, PyConfig_v311)
        _IMPL_CASE(312, PyConfig_v312)
        default: {
            break;
        }
    }

    #undef _IMPL_CASE

    return -1; /* Unsupported python version */
}


/*
 * Pre-initialize python interpreter.
 */
int
pyi_pyconfig_preinit_python(const PyiRuntimeOptions *runtime_options)
{
    PyPreConfig_Common config;

    PI_PyPreConfig_InitIsolatedConfig((PyPreConfig *)&config);
    config.utf8_mode = runtime_options->utf8_mode;

    /* Pre-initialize */
    PyStatus status = PI_Py_PreInitialize((const PyPreConfig *)&config);
    return PI_PyStatus_Exception(status) ? -1 : 0;
}
