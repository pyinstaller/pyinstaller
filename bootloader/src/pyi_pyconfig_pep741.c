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
    /* TODO */
    return -1;
}


/*
 * Set python home directory. Used to set sys.prefix.
 */
int
pyi_pyconfig_pep741_set_python_home(PyInitConfig *config, const struct PYI_CONTEXT *pyi_ctx)
{
    /* TODO */
    return -1;
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
    /* TODO */
    return -1;
}


/*
 * Set program arguments (sys.argv).
 */
int
pyi_pyconfig_pep741_set_argv(PyInitConfig *config, const struct PYI_CONTEXT *pyi_ctx)
{
    /* TODO */
    return -1;
}


/*
 * Set run-time options.
 */
int
pyi_pyconfig_pep741_set_runtime_options(PyInitConfig *config, const struct PYI_CONTEXT *pyi_ctx, const struct PyiRuntimeOptions *runtime_options)
{
    /* TODO */
    return -1;
}
