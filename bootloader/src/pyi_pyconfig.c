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
#include "pyi_archive.h"
#include "pyi_global.h"
#include "pyi_main.h"
#include "pyi_utils.h"


/*
 * Clean up and free the PyiRuntimeOptions structure created by
 * pyi_config_parse_runtime_options(). No-op if passed a NULL pointer.
 */
void
pyi_runtime_options_free(struct PyiRuntimeOptions *options)
{
    int i;

    if (options == NULL) {
        return;
    }

    /* Free the wflags array */
    if (options->num_wflags) {
        for (i = 0; i < options->num_wflags; i++) {
            free(options->wflags[i]);
        }
    }
    free(options->wflags);

    /* Free the Xflags array */
    if (options->num_xflags) {
        for (i = 0; i < options->num_xflags; i++) {
            free(options->xflags[i]);
        }
    }
    free(options->xflags);

    /* Free options structure itself */
    free(options);
}

/*
 * Helper to copy X/W flag for pass-through.
 */
static int
_pyi_copy_xwflag(const char *flag, wchar_t **pdest_buf)
{
    wchar_t flag_w[PYI_PATH_MAX + 1];

    /* Convert multi-byte string to wide-char. The multibyte encoding in PKG is UTF-8,
     * but W and X options should consist only of ASCII characters. */
    if (mbstowcs(flag_w, flag, PYI_PATH_MAX) < 0) {
        return -1;
    }

    /* Copy */
    *pdest_buf = wcsdup(flag_w);
    if (*pdest_buf == NULL) {
        return -1;
    }
    return 0;
}

/*
 * Helper that matches name of the name=value flag, and if match is
 * found, returns pointer to the value string. If the given name does
 * not match flag's name, NULL is returned. If the name matches but
 * the flag has no value, pointer to empty string (i.e., the end of
 * the flag string) is returned.
 **/
static const char *
_pyi_match_key_value_flag(const char *flag, const char *name)
{
    /* Match the name */
    size_t name_len = strlen(name);
    if (strncmp(flag, name, name_len) != 0) {
        return NULL;
    }

    /* Check for exact match flag is "name" without a value. */
    if (flag[name_len] == 0) {
        return &flag[name_len];
    }

    /* Check if flag is "name=something"; return pointer to something.
     * For compatibility reasons, also allow "name something". */
    if (flag[name_len] == '=' || flag[name_len] == ' ') {
        return &flag[name_len + 1];
    }

    /* Name is just the prefix of the flag, so no match */
    return NULL;
}

/*
 * Helper to parse an X flag to its integer value.
 */
static void
_pyi_match_and_parse_xflag(const char *flag, const char *name, int *dest_var)
{
    /* Match key/value flag */
    const char *value_str = _pyi_match_key_value_flag(flag, name);
    if (value_str == NULL) {
        return; /* No match; do not modify destination variable */
    }

    if (value_str[0] == 0)  {
        /* No value given; implicitly enabled */
        *dest_var = 1;
    } else {
        /* Value given; enabled if different from 0 */
        *dest_var = strcmp(value_str, "0") != 0;
    }
}


/*
 * Allocate the PyiRuntimeOptions structure and populate it based on
 * options found in the PKG archive.
 */
struct PyiRuntimeOptions *
pyi_runtime_options_read(const struct PYI_CONTEXT *pyi_ctx)
{
    struct PyiRuntimeOptions *options;
    const struct ARCHIVE *archive = pyi_ctx->archive;
    const struct TOC_ENTRY *toc_entry;
    int num_wflags = 0;
    int num_xflags = 0;
    int failed = 0;

    /* Allocate the structure */
    options = calloc(1, sizeof(struct PyiRuntimeOptions));
    if (options == NULL) {
        return options;
    }

    options->utf8_mode = -1; /* default: auto-select based on locale */

    /* Parse run-time options from PKG archive */
    for (toc_entry = archive->toc; toc_entry < archive->toc_end; toc_entry = pyi_archive_next_toc_entry(archive, toc_entry)) {
        const char *value_str;

        /* We are only interested in OPTION entries */
        if (toc_entry->typecode != ARCHIVE_ITEM_RUNTIME_OPTION) {
            continue;
        }

        /* Skip bootloader options; these start with "pyi-" */
        if (strncmp(toc_entry->name, "pyi-", 4) == 0) {
            continue;
        }

        /* Verbose flag: v, verbose */
        if (strcmp(toc_entry->name, "v") == 0 || strcmp(toc_entry->name, "verbose") == 0) {
            options->verbose++;
            continue;
        }

        /* Unbuffered flag: u, unbuffered */
        if (strcmp(toc_entry->name, "u") == 0 || strcmp(toc_entry->name, "unbuffered") == 0) {
            options->unbuffered = 1;
            continue;
        }

        /* Optimize flag: O, optimize */
        if (strcmp(toc_entry->name, "O") == 0 || strcmp(toc_entry->name, "optimize") == 0) {
            options->optimize++;
            continue;
        }

        /* W flag: W <warning_rule> */
        if (strncmp(toc_entry->name, "W ", 2) == 0) {
            num_wflags++;
            continue;
        }

        /* X flag: X <key=value> */
        if (strncmp(toc_entry->name, "X ", 2) == 0) {
            num_xflags++;
            continue;
        }

        /* Hash seed flag: hash_seed=value */
        value_str = _pyi_match_key_value_flag(toc_entry->name, "hash_seed");
        if (value_str && value_str[0]) {
            options->use_hash_seed = 1;
            options->hash_seed = strtoul(value_str, NULL, 10);
        }
    }

    /* Collect Wflags and Xflags for pass-through */

    /* Allocate - calloc should be safe to call with num = 0.
     * On most platforms, when called with num = 0, calloc returns a
     * non-NULL address that should be safe to free. On AIX, though,
     * it returns NULL (unless _LINUX_SOURCE_COMPAT is defined, but we
     * cannot have that defined together with _ALL_SOURCE). */
    options->wflags = calloc(num_wflags, sizeof(wchar_t *));
    options->xflags = calloc(num_xflags, sizeof(wchar_t *));
    if ((num_wflags && options->wflags == NULL) || (num_xflags && options->xflags == NULL)) {
        failed = 1;
        goto end;
    }

    /* Collect */
    for (toc_entry = archive->toc; toc_entry < archive->toc_end; toc_entry = pyi_archive_next_toc_entry(archive, toc_entry)) {
        /* We are only interested in OPTION entries */
        if (toc_entry->typecode != ARCHIVE_ITEM_RUNTIME_OPTION) {
            continue;
        }

        if (strncmp(toc_entry->name, "W ", 2) == 0) {
            /* Copy for pass-through */
            const char *flag = &toc_entry->name[2]; /* Skip first two characters */
            if (_pyi_copy_xwflag(flag, &options->wflags[options->num_wflags]) < 0) {
                failed = 1;
                goto end;
            }
            options->num_wflags++;
        } else if (strncmp(toc_entry->name, "X ", 2) == 0) {
            /* Copy for pass-through */
            const char *flag = &toc_entry->name[2]; /* Skip first two characters */
            if (_pyi_copy_xwflag(flag, &options->xflags[options->num_xflags]) < 0) {
                failed = 1;
                goto end;
            }
            options->num_xflags++;

            /* Try matching the utf8 and dev X-flag */
            _pyi_match_and_parse_xflag(flag, "utf8", &options->utf8_mode);
            _pyi_match_and_parse_xflag(flag, "dev", &options->dev_mode);
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
_pyi_pyconfig_set_string(PyConfig *config, wchar_t **dest_field, const char *str, const struct DYLIB_PYTHON *dylib_python)
{
    PyStatus status;

#ifdef _WIN32
    wchar_t *str_w;
    str_w = pyi_win32_utf8_to_wcs(str, NULL, 0);
    if (!str_w) {
        return -1;
    }
    status = dylib_python->PyConfig_SetString(config, dest_field, str_w);
    free(str_w);
#else
    status = dylib_python->PyConfig_SetBytesString(config, dest_field, str);
#endif

    return dylib_python->PyStatus_Exception(status) ? -1 : 0;
}


/* Helper for creating ID from python version and flags value */
#define _MAKE_VERSION_ID(version, flags) (version << 1 | flags)

/*
 * Allocate the PyConfig structure, based on the python version and
 * build flags.
 */
PyConfig *
pyi_pyconfig_create(const struct PYI_CONTEXT *pyi_ctx)
{
    const struct DYLIB_PYTHON *dylib_python = pyi_ctx->dylib_python;
    const int version_id = _MAKE_VERSION_ID(dylib_python->version, pyi_ctx->nogil_enabled);

    /* Macro to avoid manual code repetition. */
    #define _IMPL_CASE(PY_VERSION, PY_FLAGS, PYCONFIG_IMPL) \
    case _MAKE_VERSION_ID(PY_VERSION, PY_FLAGS): { \
        return (PyConfig *)calloc(1, sizeof(PYCONFIG_IMPL)); \
    }
    /* Macro end */

    switch (version_id) {
        _IMPL_CASE(308, 0, PyConfig_v38)
        _IMPL_CASE(309, 0, PyConfig_v39)
        _IMPL_CASE(310, 0, PyConfig_v310)
        _IMPL_CASE(311, 0, PyConfig_v311)
        _IMPL_CASE(312, 0, PyConfig_v312)
        _IMPL_CASE(313, 0, PyConfig_v313)
        _IMPL_CASE(313, 1, PyConfig_v313_GIL_DISABLED)
        default: {
            break;
        }
    }

    #undef _IMPL_CASE

    return NULL; /* Unsupported python version */
}

/*
 * Clean up and free the PyConfig structure. No-op if passed a NULL pointer.
 */
void
pyi_pyconfig_free(PyConfig *config, const struct PYI_CONTEXT *pyi_ctx)
{
    const struct DYLIB_PYTHON *dylib_python = pyi_ctx->dylib_python;

    if (config == NULL) {
        return;
    }

    /* Clear the fields that PyConfig API allocated */
    dylib_python->PyConfig_Clear(config);

    /* Free the allocated structure itself; was allocated using calloc
     * in pyi_pyconfig_create(). */
    free(config);
}

/*
 * Set program name. Used to set sys.executable, and in early error messages.
 */
int
pyi_pyconfig_set_program_name(PyConfig *config, const struct PYI_CONTEXT *pyi_ctx)
{
    const struct DYLIB_PYTHON *dylib_python = pyi_ctx->dylib_python;
    const int version_id = _MAKE_VERSION_ID(dylib_python->version, pyi_ctx->nogil_enabled);

    /* Macro to avoid manual code repetition. */
    #define _IMPL_CASE(PY_VERSION, PY_FLAGS, PYCONFIG_IMPL) \
    case _MAKE_VERSION_ID(PY_VERSION, PY_FLAGS): { \
        PYCONFIG_IMPL *config_impl = (PYCONFIG_IMPL *)config; \
        if (_pyi_pyconfig_set_string(config, &config_impl->program_name, pyi_ctx->executable_filename, dylib_python) < 0) { \
            return -1; \
        } \
        return 0; \
    }
    /* Macro end */

    switch (version_id) {
        _IMPL_CASE(308, 0, PyConfig_v38)
        _IMPL_CASE(309, 0, PyConfig_v39)
        _IMPL_CASE(310, 0, PyConfig_v310)
        _IMPL_CASE(311, 0, PyConfig_v311)
        _IMPL_CASE(312, 0, PyConfig_v312)
        _IMPL_CASE(313, 0, PyConfig_v313)
        _IMPL_CASE(313, 1, PyConfig_v313_GIL_DISABLED)
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
pyi_pyconfig_set_python_home(PyConfig *config, const struct PYI_CONTEXT *pyi_ctx)
{
    const struct DYLIB_PYTHON *dylib_python = pyi_ctx->dylib_python;
    const int version_id = _MAKE_VERSION_ID(dylib_python->version, pyi_ctx->nogil_enabled);

    /* Macro to avoid manual code repetition. */
    #define _IMPL_CASE(PY_VERSION, PY_FLAGS, PYCONFIG_IMPL) \
    case _MAKE_VERSION_ID(PY_VERSION, PY_FLAGS): { \
        PYCONFIG_IMPL *config_impl = (PYCONFIG_IMPL *)config; \
        return _pyi_pyconfig_set_string(config, &config_impl->home, pyi_ctx->application_home_dir, dylib_python); \
    }
    /* Macro end */

    switch (version_id) {
        _IMPL_CASE(308, 0, PyConfig_v38)
        _IMPL_CASE(309, 0, PyConfig_v39)
        _IMPL_CASE(310, 0, PyConfig_v310)
        _IMPL_CASE(311, 0, PyConfig_v311)
        _IMPL_CASE(312, 0, PyConfig_v312)
        _IMPL_CASE(313, 0, PyConfig_v313)
        _IMPL_CASE(313, 1, PyConfig_v313_GIL_DISABLED)
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
_pyi_pyconfig_set_module_search_paths(PyConfig *config, const struct PYI_CONTEXT *pyi_ctx, int num_paths, wchar_t **paths)
{
    const struct DYLIB_PYTHON *dylib_python = pyi_ctx->dylib_python;
    const int version_id = _MAKE_VERSION_ID(dylib_python->version, pyi_ctx->nogil_enabled);

    /* Macro to avoid manual code repetition. */
    #define _IMPL_CASE(PY_VERSION, PY_FLAGS, PYCONFIG_IMPL) \
    case _MAKE_VERSION_ID(PY_VERSION, PY_FLAGS): { \
        PyStatus status; \
        PYCONFIG_IMPL *config_impl = (PYCONFIG_IMPL *)config; \
        status = dylib_python->PyConfig_SetWideStringList(config, &config_impl->module_search_paths, num_paths, paths); \
        config_impl->module_search_paths_set = 1; \
        return dylib_python->PyStatus_Exception(status) ? -1 : 0; \
    }
    /* Macro end */

    switch (version_id) {
        _IMPL_CASE(308, 0, PyConfig_v38)
        _IMPL_CASE(309, 0, PyConfig_v39)
        _IMPL_CASE(310, 0, PyConfig_v310)
        _IMPL_CASE(311, 0, PyConfig_v311)
        _IMPL_CASE(312, 0, PyConfig_v312)
        _IMPL_CASE(313, 0, PyConfig_v313)
        _IMPL_CASE(313, 1, PyConfig_v313_GIL_DISABLED)
        default: {
            break;
        }
    }

    #undef _IMPL_CASE

    return -1; /* Unsupported python version */
}

int
pyi_pyconfig_set_module_search_paths(PyConfig *config, const struct PYI_CONTEXT *pyi_ctx)
{
#if !defined(_WIN32)
    /* Py_DecodeLocale / PyMem_RawFree in non-Windows codepath. */
    const struct DYLIB_PYTHON *dylib_python = pyi_ctx->dylib_python;
#endif

    /* TODO: instead of stitching together char strings and converting
     * them, we could probably stitch together wide-char strings directly,
     * as `home` field in config structure has already been converted. */
    char base_library_path[PYI_PATH_MAX + 1];
    char lib_dynload_path[PYI_PATH_MAX + 1];

    const char *module_search_paths[3];
    wchar_t *module_search_paths_w[3];

    int ret = 0;
    int i;

    /* home/base_library.zip */
    if (snprintf(base_library_path, PYI_PATH_MAX, "%s%c%s", pyi_ctx->application_home_dir, PYI_SEP, "base_library.zip") >= PYI_PATH_MAX) {
        return -1;
    }

    /* home/lib-dynload */
    if (snprintf(lib_dynload_path, PYI_PATH_MAX, "%s%c%s", pyi_ctx->application_home_dir, PYI_SEP, "lib-dynload") >= PYI_PATH_MAX) {
        return -1;
    }

    module_search_paths[0] = base_library_path;
    module_search_paths[1] = lib_dynload_path;
    module_search_paths[2] = pyi_ctx->application_home_dir;

    /* Convert */
    for (i = 0; i < 3; i++) {
#ifdef _WIN32
        module_search_paths_w[i] = pyi_win32_utf8_to_wcs(module_search_paths[i], NULL, 0);
#else
        module_search_paths_w[i] = dylib_python->Py_DecodeLocale(module_search_paths[i], NULL);
#endif
        if (module_search_paths_w[i] == NULL) {
            /* Do not break; we need to initialize all elements */
            ret = -1;
        }
    }
    if (ret != 0) {
        goto end; /* Conversion of at least one path failed */
    }

    /* Set */
    ret = _pyi_pyconfig_set_module_search_paths(
        config,
        pyi_ctx,
        3,
        module_search_paths_w
    );

end:
    /* Cleanup */
    for (i = 0; i < 3; i++) {
#ifdef _WIN32
        free(module_search_paths_w[i]);
#else
        dylib_python->PyMem_RawFree(module_search_paths_w[i]);
#endif
    }

    return ret;
}


/*
 * Set program arguments (sys.argv).
 */
static int
_pyi_pyconfig_set_argv(PyConfig *config, const struct PYI_CONTEXT *pyi_ctx, int argc, wchar_t **argv_w)
{
    const struct DYLIB_PYTHON *dylib_python = pyi_ctx->dylib_python;
    const int version_id = _MAKE_VERSION_ID(dylib_python->version, pyi_ctx->nogil_enabled);

    /* Macro to avoid manual code repetition. */
    #define _IMPL_CASE(PY_VERSION, PY_FLAGS, PYCONFIG_IMPL) \
    case _MAKE_VERSION_ID(PY_VERSION, PY_FLAGS): { \
        PyStatus status; \
        PYCONFIG_IMPL *config_impl = (PYCONFIG_IMPL *)config; \
        status = dylib_python->PyConfig_SetWideStringList(config, &config_impl->argv, argc, argv_w); \
        return dylib_python->PyStatus_Exception(status) ? -1 : 0; \
    }
    /* Macro end */

    switch (version_id) {
        _IMPL_CASE(308, 0, PyConfig_v38)
        _IMPL_CASE(309, 0, PyConfig_v39)
        _IMPL_CASE(310, 0, PyConfig_v310)
        _IMPL_CASE(311, 0, PyConfig_v311)
        _IMPL_CASE(312, 0, PyConfig_v312)
        _IMPL_CASE(313, 0, PyConfig_v313)
        _IMPL_CASE(313, 1, PyConfig_v313_GIL_DISABLED)
        default: {
            break;
        }
    }

    #undef _IMPL_CASE

    return -1; /* Unsupported python version */
}


#ifdef _WIN32

/* On Windows, the command-line arguments are already available in array
 * of wide-char strings, we can directly pass it into Python's
 * configuration structure. */
int
pyi_pyconfig_set_argv(PyConfig *config, const struct PYI_CONTEXT *pyi_ctx)
{
    return _pyi_pyconfig_set_argv(
        config,
        pyi_ctx,
        pyi_ctx->argc,
        pyi_ctx->argv_w
    );
}

#else /* ifdef _WIN32 */

/* On POSIX systems, we need to convert command-line arguments from
 * their local 8-bit encoding into wide-char strings used by Python
 * configuration structure. This is done using `Py_DecodeLocale`
 * function, which accounts for the locale/encoding that was set up
 * during pre-initialization of Python interpreter. */
int
pyi_pyconfig_set_argv(PyConfig *config, const struct PYI_CONTEXT *pyi_ctx)
{
    const struct DYLIB_PYTHON *dylib_python = pyi_ctx->dylib_python;
    char *const *argv;
    wchar_t **argv_w;
    int argc;
    int ret = 0;
    int i;

    /* Select original argc/argv vs. modified pyi_argc/pyi_argv */
    if (pyi_ctx->pyi_argv != NULL) {
        /* Modified pyi_argc/pyi_argv are available; use those */
        argc = pyi_ctx->pyi_argc;
        argv = pyi_ctx->pyi_argv;
    } else {
        /* Use original argc/argv */
        argc = pyi_ctx->argc;
        argv = pyi_ctx->argv;
    }

    /* Allocate */
    argv_w = calloc(argc, sizeof(wchar_t *));
    if (argv_w == NULL) {
        return -1;
    }

    /* Convert */
    for (i = 0; i < argc; i++) {
        argv_w[i] = dylib_python->Py_DecodeLocale(argv[i], NULL);
        if (argv_w[i] == NULL) {
            ret = -1;
            goto end;
        }
    }

    /* Set */
    ret = _pyi_pyconfig_set_argv(
        config,
        pyi_ctx,
        argc,
        argv_w
    );

end:
    /* Cleanup */
    for (i = 0; i < argc; i++) {
        dylib_python->PyMem_RawFree(argv_w[i]);
    }
    free(argv_w);

    return ret;
}

#endif /* ifdef _WIN32 */


/*
 * Set run-time options.
 */
int
pyi_pyconfig_set_runtime_options(PyConfig *config, const struct PYI_CONTEXT *pyi_ctx, const struct PyiRuntimeOptions *runtime_options)
{
    const struct DYLIB_PYTHON *dylib_python = pyi_ctx->dylib_python;
    const int version_id = _MAKE_VERSION_ID(dylib_python->version, pyi_ctx->nogil_enabled);

    /* *** Common options *** */
    /* Macro to avoid manual code repetition. */
    #define _IMPL_CASE(PY_VERSION, PY_FLAGS, PYCONFIG_IMPL) \
    case _MAKE_VERSION_ID(PY_VERSION, PY_FLAGS): { \
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
        /* Hash seed */ \
        config_impl->use_hash_seed = runtime_options->use_hash_seed; \
        config_impl->hash_seed = runtime_options->hash_seed; \
        /* We enable dev_mode in pre-init config, but it seems we need to do it here again. */ \
        config_impl->dev_mode = runtime_options->dev_mode; \
        /* Set W-flags, if available */ \
        if (runtime_options->num_wflags) { \
            status = dylib_python->PyConfig_SetWideStringList(config, &config_impl->warnoptions, runtime_options->num_wflags, runtime_options->wflags); \
            if (dylib_python->PyStatus_Exception(status)) { \
                return -1; \
            } \
        } \
        /* Set X-flags, if available. Note that this is just pass-through that allows options to show up in sys._xoptions;
         * for example, for -Xutf8 or -Xdev to take effect, we need to explicitly parse them and modify PyConfig fields. */ \
        if (runtime_options->num_xflags) { \
            status = dylib_python->PyConfig_SetWideStringList(config, &config_impl->xoptions, runtime_options->num_xflags, runtime_options->xflags); \
            if (dylib_python->PyStatus_Exception(status)) { \
                return -1; \
            } \
        } \
        /* Set install_signal_handlers to match behavior of bootloader from PyInstaller 5.x and earlier.
         * There, interpreter was initialized via Py_Initialize(), which in turn calls Py_InitializeEx(1),
         * i.e., with initsigs=1). Failing to install signal handlers leads to problems with `time.sleep()`
         * on Python <= 3.8.6 and Python 3.9.0 under Windows; see:
         * https://github.com/pyinstaller/pyinstaller/issues/8104
         * https://bugs.python.org/issue41686
         */ \
        config_impl->install_signal_handlers = 1; \
        return 0; \
    }
    /* Macro end */

    switch (version_id) {
        _IMPL_CASE(308, 0, PyConfig_v38)
        _IMPL_CASE(309, 0, PyConfig_v39)
        _IMPL_CASE(310, 0, PyConfig_v310)
        _IMPL_CASE(311, 0, PyConfig_v311)
        _IMPL_CASE(312, 0, PyConfig_v312)
        _IMPL_CASE(313, 0, PyConfig_v313)
        _IMPL_CASE(313, 1, PyConfig_v313_GIL_DISABLED)
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
pyi_pyconfig_preinit_python(const struct PyiRuntimeOptions *runtime_options, const struct PYI_CONTEXT *pyi_ctx)
{
    const struct DYLIB_PYTHON *dylib_python = pyi_ctx->dylib_python;
    PyPreConfig_Common config;
    PyStatus status;

    dylib_python->PyPreConfig_InitIsolatedConfig((PyPreConfig *)&config);

    config.utf8_mode = runtime_options->utf8_mode;
    config.dev_mode = runtime_options->dev_mode;

    /* Set the LC_CTYPE locale to the user-preferred locale, so it can be read using `locale.getlocale()` in python code. */
    config.configure_locale = 1;

    /* Pre-initialize */
    status = dylib_python->Py_PreInitialize((const PyPreConfig *)&config);
    return dylib_python->PyStatus_Exception(status) ? -1 : 0;
}
