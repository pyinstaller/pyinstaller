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

#ifndef PYI_PYCONFIG_V313_H
#define PYI_PYCONFIG_V313_H

#include "pyi_global.h"
#include <wchar.h>

/* Ensure that the "optional" fields at the end of the config structure
 * are always enabled, since we have no way of knowing whether a particular
 * build has them enabled or not (nor do we want to provide precompiled
 * bootloaders for each variant). Worst case, we allocate some unused fields
 * at the end of the structure on the heap - and as long as we do not have
 * to touch those fields, the layout of that part does not matter to us
 * (as long as it is large enough to accommodate python's code accessing
 * it, if necessary).
 */
#define Py_STATS 1
#define Py_DEBUG 1

/* PyConfig structure for Python 3.13
 * https://github.com/python/cpython/blob/v3.13.0a2/Include/cpython/initconfig.h
 */
typedef struct {
    int _config_init;

    int isolated;
    int use_environment;
    int dev_mode;
    int install_signal_handlers;
    int use_hash_seed;
    unsigned long hash_seed;
    int faulthandler;
    int tracemalloc;
    int perf_profiling;
    int import_time;
    int code_debug_ranges;
    int show_ref_count;
    int dump_refs;
    wchar_t *dump_refs_file;
    int malloc_stats;
    wchar_t *filesystem_encoding;
    wchar_t *filesystem_errors;
    wchar_t *pycache_prefix;
    int parse_argv;
    PyWideStringList orig_argv;
    PyWideStringList argv;
    PyWideStringList xoptions;
    PyWideStringList warnoptions;
    int site_import;
    int bytes_warning;
    int warn_default_encoding;
    int inspect;
    int interactive;
    int optimization_level;
    int parser_debug;
    int write_bytecode;
    int verbose;
    int quiet;
    int user_site_directory;
    int configure_c_stdio;
    int buffered_stdio;
    wchar_t *stdio_encoding;
    wchar_t *stdio_errors;
#ifdef MS_WINDOWS
    int legacy_windows_stdio;
#endif
    wchar_t *check_hash_pycs_mode;
    int use_frozen_modules;
    int safe_path;
    int int_max_str_digits;

    int cpu_count;

    int pathconfig_warnings;
    wchar_t *program_name;
    wchar_t *pythonpath_env;
    wchar_t *home;
    wchar_t *platlibdir;

    int module_search_paths_set;
    PyWideStringList module_search_paths;
    wchar_t *stdlib_dir;
    wchar_t *executable;
    wchar_t *base_executable;
    wchar_t *prefix;
    wchar_t *base_prefix;
    wchar_t *exec_prefix;
    wchar_t *base_exec_prefix;

    int skip_source_first_line;
    wchar_t *run_command;
    wchar_t *run_module;
    wchar_t *run_filename;

    wchar_t *sys_path_0;

    int _install_importlib;
    int _init_main;
    int _is_python_build;

#ifdef Py_STATS
    int _pystats;
#endif

#ifdef Py_DEBUG
    wchar_t *run_presite;
#endif
} PyConfig_v313;

/* Keep these defines local to this header file... */
#undef Py_STATS
#undef Py_DEBUG

#endif /* PYI_PYCONFIG_V312_H */
