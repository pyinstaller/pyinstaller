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

#ifndef PYI_PYCONFIG_V38_H
#define PYI_PYCONFIG_V38_H

#include "pyi_global.h"
#include <wchar.h>

/* PyConfig structure for Python 3.11
 * https://github.com/python/cpython/blob/v3.11.0/Include/cpython/initconfig.h
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
    int import_time;
    int show_ref_count;
    int show_alloc_count;
    int dump_refs;
    int malloc_stats;
    wchar_t *filesystem_encoding;
    wchar_t *filesystem_errors;
    wchar_t *pycache_prefix;
    int parse_argv;
    PyWideStringList argv;
    wchar_t *program_name;
    PyWideStringList xoptions;
    PyWideStringList warnoptions;
    int site_import;
    int bytes_warning;
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
    int pathconfig_warnings;
    wchar_t *pythonpath_env;
    wchar_t *home;

    int module_search_paths_set;
    PyWideStringList module_search_paths;
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

    int _install_importlib;
    int _init_main;
} PyConfig_v38;

#endif /* PYI_PYCONFIG_V38_H */
