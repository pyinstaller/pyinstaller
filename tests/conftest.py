#-----------------------------------------------------------------------------
# Copyright (c) 2005-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

# Wraps the in-package PyInstaller test harness (PyInstaller.utils.conftest) for PyInstaller's own test suite. The
# machinery itself lives in the package because it is also the supported hook-testing surface consumed by
# pyinstaller-hooks-contrib (see the `hook_testing` extra in pyproject.toml).

import os
import pathlib
import shutil
import sys

import pytest

from PyInstaller.compat import is_darwin, is_win

# Make the checked-out PyInstaller importable even when it is not installed (the repository root is the parent of
# this directory).
_ROOT_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.append(_ROOT_DIR)

# Bring the harness fixtures and hooks into this file.
from PyInstaller.utils.conftest import *  # noqa: F401, F403, E402


# A fixture that compiles a test shared library from `functional/data/ctypes_dylib/ctypes_dylib.c` into a
# session-scoped temporary directory, and returns path to the compiled shared library. It lives on this side of the
# harness because its data directory is specific to PyInstaller's own test suite.
@pytest.fixture(scope="session")
def compiled_dylib(tmp_path_factory):
    # Copy the source to temporary directory.
    orig_source_dir = pathlib.Path(__file__).parent / 'functional' / 'data' / 'ctypes_dylib'
    tmp_source_dir = tmp_path_factory.mktemp('compiled_ctypes_dylib')
    shutil.copy2(orig_source_dir / 'ctypes_dylib.c', tmp_source_dir)

    # Compile shared library using `distuils.ccompiler` module. The code is loosely based on implementation of the
    # `distutils.command.build_ext` command module.
    def _compile_dylib(source_dir):
        # Until python 3.12, `distutils` was part of standard library. For newer python versions, `setuptools` provides
        # its vendored copy. If neither are available, skip the test.
        try:
            import distutils.ccompiler
            import distutils.sysconfig
        except ImportError:
            pytest.skip('distutils.ccompiler is not available')

        # Set up compiler
        compiler = distutils.ccompiler.new_compiler()
        distutils.sysconfig.customize_compiler(compiler)
        if hasattr(compiler, 'initialize'):  # Applicable to MSVCCompiler on Windows.
            compiler.initialize()

        if is_win:
            # With MinGW compiler, the `customize_compiler()` call ends up changing `compiler.shared_lib_extension` into
            # ".pyd". Use ".dll" instead.
            suffix = '.dll'
        elif is_darwin:
            # On macOS, `compiler.shared_lib_extension` is ".so", but ".dylib" is more appropriate.
            suffix = '.dylib'
        else:
            suffix = compiler.shared_lib_extension

        # Change the current working directory to the directory that contains source files. Ideally, we could pass the
        # absolute path to sources to `compiler.compile()` and set its `output_dir` argument to the directory where
        # object files should be generated. However, in this case, the object files are put under output directory
        # *while retaining their original path component*. If `output_dir` is not specified, then the original absolute
        # source file paths seem to be turned into relative ones (e.g, on Linux, the leading / is stripped away).
        #
        # NOTE: with python >= 3.11 we could use contextlib.chdir().
        old_cwd = pathlib.Path.cwd()
        os.chdir(source_dir)
        try:
            # Compile source .c file into object
            sources = [
                'ctypes_dylib.c',
            ]
            objects = compiler.compile(sources)

            # Link into shared library
            output_filename = f'ctypes_dylib{suffix}'
            compiler.link_shared_object(
                objects,
                output_filename,
                target_lang='c',
                export_symbols=['add_twelve'],
            )
        finally:
            os.chdir(old_cwd)  # Restore old working directory.

        # Return path to compiled shared library
        return source_dir / output_filename

    try:
        return _compile_dylib(tmp_source_dir)
    except Exception as e:
        pytest.skip(f"Could not compile test shared library: {e}")
