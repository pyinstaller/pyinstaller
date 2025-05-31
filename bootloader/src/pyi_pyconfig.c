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
 * Functions to deal with python initialization configuration.
 */

#include <stdlib.h>
#include <string.h>

#include "pyi_pyconfig.h"
#include "pyi_archive.h"
#include "pyi_global.h"
#include "pyi_main.h"
#include "pyi_utils.h"


/* wcsdup() is unavailable on some (older) platforms, such as Solaris 10. */
#ifndef HAVE_WCSDUP

static wchar_t *
wcsdup(const wchar_t *s)
{
    size_t len = wcslen(s) + 1;
    wchar_t *new_s = malloc(len * sizeof(wchar_t));
    if (new_s) {
        wcscpy(new_s, s);
    }
    return new_s;
}

#endif


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
        if (options->wflags) {
            for (i = 0; i < options->num_wflags; i++) {
                free(options->wflags[i]);
            }
        }
        if (options->wflags_w) {
            for (i = 0; i < options->num_wflags; i++) {
                free(options->wflags_w[i]);
            }
        }
    }
    free(options->wflags);
    free(options->wflags_w);

    /* Free the Xflags array */
    if (options->num_xflags) {
        if (options->xflags) {
            for (i = 0; i < options->num_xflags; i++) {
                free(options->xflags[i]);
            }
        }
        if (options->xflags_w) {
            for (i = 0; i < options->num_xflags; i++) {
                free(options->xflags_w[i]);
            }
        }
    }
    free(options->xflags);
    free(options->xflags_w);

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

    const unsigned char use_pep741 = pyi_ctx->dylib_python->has_pep741;

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

    /* For PEP 741 codepath, we collect into narrow-char string arrays
     * (options->wflags and options->xflags). For older PEP 587 codepath,
     * we convert and collect into wide-char string arrays (options->wflags_w
     * and options->xflags_w). This minimizes the amount of conversions
     * and simplifies the configuration code (which can just pass string
     * arrays to corresponding functions). */

    /* Allocate - calloc should be safe to call with num = 0.
     * On most platforms, when called with num = 0, calloc returns a
     * non-NULL address that should be safe to free. On AIX, though,
     * it returns NULL (unless _LINUX_SOURCE_COMPAT is defined, but we
     * cannot have that defined together with _ALL_SOURCE). */
    if (use_pep741) {
        options->wflags = calloc(num_wflags, sizeof(char *));
        options->xflags = calloc(num_xflags, sizeof(char *));
        if ((num_wflags && options->wflags == NULL) || (num_xflags && options->xflags == NULL)) {
            failed = 1;
            goto end;
        }
    } else {
        options->wflags_w = calloc(num_wflags, sizeof(wchar_t *));
        options->xflags_w = calloc(num_xflags, sizeof(wchar_t *));
        if ((num_wflags && options->wflags_w == NULL) || (num_xflags && options->xflags_w == NULL)) {
            failed = 1;
            goto end;
        }
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
            if (use_pep741) {
                /* Copy into narrow-char string array for PEP 741 codepath */
                char *flag_dup = strdup(flag);
                if (flag_dup == NULL) {
                    failed = 1;
                    goto end;
                }
                options->wflags[options->num_wflags] = flag_dup;
            } else {
                /* Convert and copy into wide-char string array for PEP 587 codepath */
                if (_pyi_copy_xwflag(flag, &options->wflags_w[options->num_wflags]) < 0) {
                    failed = 1;
                    goto end;
                }
            }
            options->num_wflags++;
        } else if (strncmp(toc_entry->name, "X ", 2) == 0) {
            /* Copy for pass-through */
            const char *flag = &toc_entry->name[2]; /* Skip first two characters */
            if (use_pep741) {
                /* Copy into narrow-char string array for PEP 741 codepath */
                char *flag_dup = strdup(flag);
                if (flag_dup == NULL) {
                    failed = 1;
                    goto end;
                }
                options->xflags[options->num_wflags] = flag_dup;
            } else {
                /* Convert and copy into wide-char string array for PEP 587 codepath */
                if (_pyi_copy_xwflag(flag, &options->xflags_w[options->num_xflags]) < 0) {
                    failed = 1;
                    goto end;
                }
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
