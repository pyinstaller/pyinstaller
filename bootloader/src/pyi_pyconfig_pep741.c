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


static char *_wchar_to_utf8(const wchar_t *string_w)
{
    char *buffer;
    char *ptr;
    size_t len;
    size_t i;

    /* For each input wide-character, the worst-case output is four bytes.
     * Plus, we need a terminating NUL character. Make sure that the
     * required buffer size still fits into size_t. */
    len = wcslen(string_w);
    if (len + 1 > (SIZE_MAX / 4)) {
        return NULL;
    }

    buffer = malloc((len + 1) * 4);
    if (buffer == NULL) {
        return NULL;
    }

    ptr = buffer;
    i = 0;
    while (i < len) {
        int32_t ch = string_w[i];
        i++;

        /* Handle UTF-16 surrogates (applicable only when sizeof(wchar_t) == 2);
         * with UTF-32, these codepoints are invalid, and in the unlikely
         * case they appear, we pass them through. */
        if (0xD800 <= ch && ch <= 0xDBFF && i < len) {
            int32_t next_ch = string_w[i];
            if (0xDC00 <= next_ch && next_ch <= 0xDFFF) {
                ch = 0x10000 + (((ch & 0x03FF) << 10) | (next_ch & 0x03FF));
                i++;
            }
        }

        if (ch < 0x80) {
            *ptr++ = (char) ch;
        } else if (ch < 0x0800) {
            *ptr++ = (char)(0xc0 | (ch >> 6));
            *ptr++ = (char)(0x80 | (ch & 0x3f));
        } else if (ch < 0x10000) {
            *ptr++ = (char)(0xe0 | (ch >> 12));
            *ptr++ = (char)(0x80 | ((ch >> 6) & 0x3f));
            *ptr++ = (char)(0x80 | (ch & 0x3f));
        } else {
            *ptr++ = (char)(0xf0 | (ch >> 18));
            *ptr++ = (char)(0x80 | ((ch >> 12) & 0x3f));
            *ptr++ = (char)(0x80 | ((ch >> 6) & 0x3f));
            *ptr++ = (char)(0x80 | (ch & 0x3f));
        }
    }
    *ptr++ = 0;

    return buffer;
}


static char *
_locale_encoding_to_utf8(
    const char *string,
    char *output_buffer,
    size_t output_buffer_size,
    const struct DYLIB_PYTHON *dylib_python
)
{
    wchar_t *string_w;
    char *string_utf8;

    /* Convert from locale encoding to wide-char using Py_DecodeLocale() */;
    string_w = dylib_python->Py_DecodeLocale(string, NULL);
    if (string_w == NULL) {
        return NULL;
    }

    /* Now convert wide-char (UTF-16 or UTF-32, depending on platform and
     * its width of wchar_t type) to UTF-8. */
    string_utf8 = _wchar_to_utf8(string_w);

    dylib_python->PyMem_RawFree(string_w);

    /* If output buffer is provided, copy the string into it. */
    if (output_buffer) {
        int ret;

        ret = snprintf(output_buffer, output_buffer_size, "%s", string_utf8);
        free(string_utf8);
        if (ret < 0 || (size_t)ret >= output_buffer_size) {
            return NULL;
        }
        return output_buffer;
    }

    /* Otherwise, return the original UTF-8 buffer and let the caller
     * free() it. */
    return string_utf8;
}


/*
 * Set program name. Used to set sys.executable, and in early error messages.
 */
int
pyi_pyconfig_pep741_set_program_name(PyInitConfig *config, const struct PYI_CONTEXT *pyi_ctx)
{
    const struct DYLIB_PYTHON *dylib_python = pyi_ctx->dylib_python;

#if defined(_WIN32)
    /* On Windows, pyi_ctx->executable_filename is already in UTF-8. */
    const char *program_name_utf8 = pyi_ctx->executable_filename;
#else
    char program_name_utf8[PYI_PATH_MAX];
    if (_locale_encoding_to_utf8(pyi_ctx->executable_filename, program_name_utf8, PYI_PATH_MAX, dylib_python) == NULL) {
        PYI_ERROR("Failed to convert executable filename to UTF-8.\n");
        return -1;
    }
#endif

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

#if defined(_WIN32)
    /* On Windows, pyi_ctx->application_home_dir is already in UTF-8 */
    const char *python_home_utf8 = pyi_ctx->application_home_dir;
#else
    char python_home_utf8[PYI_PATH_MAX];
    if (_locale_encoding_to_utf8(pyi_ctx->application_home_dir, python_home_utf8, PYI_PATH_MAX, dylib_python) == NULL) {
        PYI_ERROR("Failed to convert application home directory to UTF-8.\n");
        return -1;
    }
#endif

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

    char home_dir_utf8[PYI_PATH_MAX];
    char base_library_path_utf8[PYI_PATH_MAX];
    char lib_dynload_path_utf8[PYI_PATH_MAX];

    char *module_search_paths_utf8[3];

    /* On Windows, the pyi_ctx->application_home_dir is already in UTF-8.
     * On other platforms, we need to convert it, but then we can use
     * the converted string as base for other paths. */

    /* home */
#if defined(_WIN32)
    if (snprintf(home_dir_utf8, PYI_PATH_MAX, "%s", pyi_ctx->application_home_dir) >= PYI_PATH_MAX) {
        PYI_ERROR("Failed to copy path to application home directory - path is too long!\n");
        return -1;
    }
#else
    if (_locale_encoding_to_utf8(pyi_ctx->application_home_dir, home_dir_utf8, PYI_PATH_MAX, dylib_python) == NULL) {
        PYI_ERROR("Failed to convert path to application home directory to UTF-8!\n");
        return -1;
    }
#endif

    /* home/base_library.zip */
    if (snprintf(base_library_path_utf8, PYI_PATH_MAX, "%s%c%s", home_dir_utf8, PYI_SEP, "base_library.zip") >= PYI_PATH_MAX) {
        PYI_ERROR("Failed to construct path to base_library.zip - path is too long!\n");
        return -1;
    }

    /* home/lib-dynload */
    if (snprintf(lib_dynload_path_utf8, PYI_PATH_MAX, "%s%c%s", home_dir_utf8, PYI_SEP, "lib-dynload") >= PYI_PATH_MAX) {
        PYI_ERROR("Failed to construct path to lib-dynload directory - path is too long!\n");
        return -1;
    }

    module_search_paths_utf8[0] = base_library_path_utf8;
    module_search_paths_utf8[1] = lib_dynload_path_utf8;
    module_search_paths_utf8[2] = home_dir_utf8;

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
 *
 * On Windows, we have the original argv available in wide-char format,
 * so we need to convert it to UTF-8 narrow-char string array. On
 * other platforms, argv is in locale encoding, and also needs to
 * be converted to UTF-8. */
int
pyi_pyconfig_pep741_set_argv(PyInitConfig *config, const struct PYI_CONTEXT *pyi_ctx)
{
    const struct DYLIB_PYTHON *dylib_python = pyi_ctx->dylib_python;
    int ret = 0;

    int argc;
    char **argv_utf8;
    int i;

#if defined(_WIN32)
    argc = pyi_ctx->argc;
#else
    char **argv;

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
#endif

    /* Allocate */
    argv_utf8 = calloc(argc, sizeof(char *));
    if (argv_utf8 == NULL) {
        return -1;
    }

    /* Convert */
    for (i = 0; i < argc; i++) {
#if defined(_WIN32)
        argv_utf8[i] = pyi_win32_wcs_to_utf8(pyi_ctx->argv_w[i], NULL, 0);
#else
        argv_utf8[i] = _locale_encoding_to_utf8(argv[i], NULL, 0, dylib_python);
#endif
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
