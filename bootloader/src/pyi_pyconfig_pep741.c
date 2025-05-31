/*
 * ****************************************************************************
 * Copyright (c) 2025, PyInstaller Development Team.
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
 * Functions to deal with PEP 741 python initialization configuration.
 *
 * NOTE: in contrast to PEP 587 API where wide-char strings are used
 * (PyConfig_SetString, PyConfig_SetWideStringList) and narrow-char
 * strings are assumed to be in the locale encoding (PyConfig_SetBytesString),
 * PEP 741 API uses narrow-char strings in UTF-8 encoding (PyInitConfig_SetStr,
 * PyInitConfig_SetStrList). On Windows, any narrow-char strings we have
 * are already in UTF-8 encoding. On POSIX systems, they are in locale
 * encoding, and need to be converted to UTF-8; unless locale encoding
 * also happens to be UTF-8, but aside from macOS, we cannot assume that.
 */

#include <stdlib.h>
#include <string.h>

#include "pyi_pyconfig.h"
#include "pyi_archive.h"
#include "pyi_dylib_python.h"
#include "pyi_global.h"
#include "pyi_main.h"
#include "pyi_utils.h"


/*
 * Set program name. Used to set sys.executable, and in early error messages.
 */
int
pyi_pyconfig_pep741_set_program_name(PyInitConfig *config, const struct PYI_CONTEXT *pyi_ctx)
{
    const struct DYLIB_PYTHON *dylib_python = pyi_ctx->dylib_python;

    /* TODO: ensure proper conversion to UTF-8 where necessary */
    const char *program_name_utf8 = pyi_ctx->executable_filename;

    if (dylib_python->PyInitConfig_SetStr(config, "program_name", program_name_utf8) < 0) {
        const char *error_message = NULL;
        dylib_python->PyInitConfig_GetError(config, &error_message);
        PYI_ERROR("Failed to set program name: %s\n", error_message);
        return -1;
    }

    return 0;
}


/*
 * Set python home directory. Used to set sys.prefix.
 */
int
pyi_pyconfig_pep741_set_python_home(PyInitConfig *config, const struct PYI_CONTEXT *pyi_ctx)
{
    const struct DYLIB_PYTHON *dylib_python = pyi_ctx->dylib_python;

    /* TODO: ensure proper conversion to UTF-8 where necessary */
    const char *python_home_utf8 = pyi_ctx->application_home_dir;

    if (dylib_python->PyInitConfig_SetStr(config, "home", python_home_utf8) < 0) {
        const char *error_message = NULL;
        dylib_python->PyInitConfig_GetError(config, &error_message);
        PYI_ERROR("Failed to set python home path: %s\n", error_message);
        return -1;
    }

    return 0;
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
int
pyi_pyconfig_pep741_set_module_search_paths(PyInitConfig *config, const struct PYI_CONTEXT *pyi_ctx)
{
    const struct DYLIB_PYTHON *dylib_python = pyi_ctx->dylib_python;

    char home_dir[PYI_PATH_MAX + 1];
    char base_library_path[PYI_PATH_MAX + 1];
    char lib_dynload_path[PYI_PATH_MAX + 1];

    char *module_search_paths_utf8[3];

    /* TODO: ensure proper conversion to UTF-8 where necessary */

    /* home */
    if (snprintf(home_dir, PYI_PATH_MAX, "%s", pyi_ctx->application_home_dir) >= PYI_PATH_MAX) {
        return -1;
    }

    /* home/base_library.zip */
    if (snprintf(base_library_path, PYI_PATH_MAX, "%s%c%s", home_dir, PYI_SEP, "base_library.zip") >= PYI_PATH_MAX) {
        return -1;
    }

    /* home/lib-dynload */
    if (snprintf(lib_dynload_path, PYI_PATH_MAX, "%s%c%s", home_dir, PYI_SEP, "lib-dynload") >= PYI_PATH_MAX) {
        return -1;
    }

    module_search_paths_utf8[0] = base_library_path;
    module_search_paths_utf8[1] = lib_dynload_path;
    module_search_paths_utf8[2] = home_dir;

    if (dylib_python->PyInitConfig_SetStrList(config, "module_search_paths", 3, module_search_paths_utf8) < 0) {
        const char *error_message = NULL;
        dylib_python->PyInitConfig_GetError(config, &error_message);
        PYI_ERROR("Failed to set module search paths: %s\n", error_message);
        return -1;
    }

    return 0;
}


/*
 * Set program arguments (sys.argv).
 */
#ifdef _WIN32

/* On Windows, we have the original argv available in wide-char format,
 * so we need to convert it to UTF-8 narrow-char string array. */

int
pyi_pyconfig_pep741_set_argv(PyInitConfig *config, const struct PYI_CONTEXT *pyi_ctx)
{
    const struct DYLIB_PYTHON *dylib_python = pyi_ctx->dylib_python;
    int ret = 0;

    int argc;
    char **argv_utf8;
    int i;

    /* Allocate */
    argc = pyi_ctx->argc;
    argv_utf8 = calloc(argc, sizeof(char *));
    if (argv_utf8 == NULL) {
        return -1;
    }

    /* Convert */
    for (i = 0; i < argc; i++) {
        argv_utf8[i] = pyi_win32_wcs_to_utf8(pyi_ctx->argv_w[i], NULL, 0);
        if (argv_utf8[i] == NULL) {
            ret = -1;
            goto end;
        }
    }

    /* Set */
    if (dylib_python->PyInitConfig_SetStrList(config, "argv", argc, argv_utf8) < 0) {
        const char *error_message = NULL;
        dylib_python->PyInitConfig_GetError(config, &error_message);
        PYI_ERROR("Failed to set sys.argv: %s\n", error_message);
        ret = -1;
    }

end:
    /* Cleanup */
    for (i = 0; i < argc; i++) {
        free(argv_utf8[i]);
    }
    free(argv_utf8);

    return ret;
}

#else

int
pyi_pyconfig_pep741_set_argv(PyInitConfig *config, const struct PYI_CONTEXT *pyi_ctx)
{
    const struct DYLIB_PYTHON *dylib_python = pyi_ctx->dylib_python;

    int argc;
    char **argv_utf8;

    /* Select original argc/argv vs. modified pyi_argc/pyi_argv */
    /* TODO: ensure proper conversion to UTF-8 where necessary */
    if (pyi_ctx->pyi_argv != NULL) {
        /* Modified pyi_argc/pyi_argv are available; use those */
        argc = pyi_ctx->pyi_argc;
        argv_utf8 = pyi_ctx->pyi_argv;
    } else {
        /* Use original argc/argv */
        argc = pyi_ctx->argc;
        argv_utf8 = pyi_ctx->argv;
    }

    if (dylib_python->PyInitConfig_SetStrList(config, "argv", argc, argv_utf8) < 0) {
        const char *error_message = NULL;
        dylib_python->PyInitConfig_GetError(config, &error_message);
        PYI_ERROR("Failed to set sys.argv: %s\n", error_message);
        return -1;
    }

    return 0;
}

#endif


/*
 * Set run-time options.
 */
int
pyi_pyconfig_pep741_set_runtime_options(PyInitConfig *config, const struct PYI_CONTEXT *pyi_ctx, const struct PyiRuntimeOptions *runtime_options)
{
    const struct DYLIB_PYTHON *dylib_python = pyi_ctx->dylib_python;
    const char *error_message = NULL;

    /* Disable site */
    if (dylib_python->PyInitConfig_SetInt(config, "site_import", 0) < 0) {
        dylib_python->PyInitConfig_GetError(config, &error_message);
        PYI_ERROR("Failed to set 'site_import': %s\n", error_message);
        return -1;
    }

    /* Do not write bytecode */
    if (dylib_python->PyInitConfig_SetInt(config, "write_bytecode", 0) < 0) {
        dylib_python->PyInitConfig_GetError(config, &error_message);
        PYI_ERROR("Failed to set 'write_bytecode': %s\n", error_message);
        return -1;
    }

    /* Configure C standard I/O streams (e.g., to apply buffered/unbuffered mode */
    if (dylib_python->PyInitConfig_SetInt(config, "configure_c_stdio", 0) < 0) {
        dylib_python->PyInitConfig_GetError(config, &error_message);
        PYI_ERROR("Failed to set 'configure_c_stdio': %s\n", error_message);
        return -1;
    }

    /* Set optimization level */
    if (dylib_python->PyInitConfig_SetInt(config, "optimization_level", runtime_options->optimize) < 0) {
        dylib_python->PyInitConfig_GetError(config, &error_message);
        PYI_ERROR("Failed to set 'optimization_level': %s\n", error_message);
        return -1;
    }

    /* Set buffered/unbuffered standard I/O streams */
    if (dylib_python->PyInitConfig_SetInt(config, "buffered_stdio", !runtime_options->unbuffered) < 0) {
        dylib_python->PyInitConfig_GetError(config, &error_message);
        PYI_ERROR("Failed to set 'buffered_stdio': %s\n", error_message);
        return -1;
    }

    /* Import verbosity */
    if (dylib_python->PyInitConfig_SetInt(config, "verbose", runtime_options->verbose) < 0) {
        dylib_python->PyInitConfig_GetError(config, &error_message);
        PYI_ERROR("Failed to set 'verbose': %s\n", error_message);
        return -1;
    }

    /* Hash seed setting */
    if (dylib_python->PyInitConfig_SetInt(config, "use_hash_seed", runtime_options->use_hash_seed) < 0) {
        dylib_python->PyInitConfig_GetError(config, &error_message);
        PYI_ERROR("Failed to set 'use_hash_seed': %s\n", error_message);
        return -1;
    }

    if (dylib_python->PyInitConfig_SetInt(config, "hash_seed", runtime_options->hash_seed) < 0) {
        dylib_python->PyInitConfig_GetError(config, &error_message);
        PYI_ERROR("Failed to set 'hash_seed': %s\n", error_message);
        return -1;
    }

    /* Dev mode; should already be set during interpreter pre-initialization,
     * but set it again, just in case. */
    if (dylib_python->PyInitConfig_SetInt(config, "dev_mode", runtime_options->dev_mode) < 0) {
        dylib_python->PyInitConfig_GetError(config, &error_message);
        PYI_ERROR("Failed to set 'dev_mode': %s\n", error_message);
        return -1;
    }

    /* Have python install signal handlers */
    if (dylib_python->PyInitConfig_SetInt(config, "install_signal_handlers", 1) < 0) {
        dylib_python->PyInitConfig_GetError(config, &error_message);
        PYI_ERROR("Failed to set 'install_signal_handlers': %s\n", error_message);
        return -1;
    }

    /* Apply W-flags and X-flags */
    /* For simplicity, our run-time flag parser code collects these into
     * narrow-char string arrays (which should contain only ASCII characters
     * anyway) */
    if (dylib_python->PyInitConfig_SetStrList(config, "warnoptions", runtime_options->num_wflags, runtime_options->wflags) < 0) {
        dylib_python->PyInitConfig_GetError(config, &error_message);
        PYI_ERROR("Failed to set 'warnoptions': %s\n", error_message);
        return -1;
    }

    if (dylib_python->PyInitConfig_SetStrList(config, "xoptions", runtime_options->num_xflags, runtime_options->xflags) < 0) {
        dylib_python->PyInitConfig_GetError(config, &error_message);
        PYI_ERROR("Failed to set 'xoptions': %s\n", error_message);
        return -1;
    }

    return 0;
}
