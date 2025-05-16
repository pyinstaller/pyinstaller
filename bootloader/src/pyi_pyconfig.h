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
 *
 * These helpers allow the rest of bootloader to pretend that PEP 587 has
 * a sane API with opaque types.
 */

#ifndef PYI_PYCONFIG_H
#define PYI_PYCONFIG_H

#include "pyi_dylib_python.h"

struct PYI_CONTEXT;


/* Collect run-time options from PKG */
struct PyiRuntimeOptions
{
    int verbose;
    int unbuffered;
    int optimize;

    int use_hash_seed;
    unsigned long hash_seed;

    int utf8_mode;
    int dev_mode;

    int num_wflags;
    wchar_t **wflags;

    int num_xflags;
    wchar_t **xflags;
};

struct PyiRuntimeOptions *pyi_runtime_options_read(const struct PYI_CONTEXT *pyi_ctx);
void pyi_runtime_options_free(struct PyiRuntimeOptions *options);

/* PEP 587 helpers */
PyConfig *pyi_pyconfig_create(const struct PYI_CONTEXT *pyi_ctx);
void pyi_pyconfig_free(PyConfig *config, const struct PYI_CONTEXT *pyi_ctx);

int pyi_pyconfig_set_program_name(PyConfig *config, const struct PYI_CONTEXT *pyi_ctx);
int pyi_pyconfig_set_python_home(PyConfig *config, const struct PYI_CONTEXT *pyi_ctx);
int pyi_pyconfig_set_module_search_paths(PyConfig *config, const struct PYI_CONTEXT *pyi_ctx);
int pyi_pyconfig_set_argv(PyConfig *config, const struct PYI_CONTEXT *pyi_ctx);
int pyi_pyconfig_set_runtime_options(PyConfig *config, const struct PYI_CONTEXT *pyi_ctx, const struct PyiRuntimeOptions *runtime_options);

int pyi_pyconfig_preinit_python(const struct PyiRuntimeOptions *runtime_options, const struct PYI_CONTEXT *pyi_ctx);

#endif /* PYI_PYCONFIG_H */
