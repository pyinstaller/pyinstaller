#-----------------------------------------------------------------------------
# Copyright (c) 2021-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import sys

from PyInstaller.depend import bindepend


def test_library_matcher():
    """
    Test that _library_matcher() is tolerant to version numbers both before and after the .so suffix but does not
    allow runaway glob patterns to match anything else.
    """
    m = bindepend._library_matcher("libc")
    assert m("libc.so")
    assert m("libc.dylib")
    assert m("libc.so.1")
    assert not m("libcrypt.so")

    m = bindepend._library_matcher("libpng")
    assert m("libpng16.so.16")


def test_binary_dependency_analysis():
    """
    Test that binary dependency analysis works, by running it on a binary (executable or shared library) and checking
    that at least one dependency is reported.
    """
    # Check both python interpreter executable and python shared library. Often, the python executable is linked against
    # the python shared library (but now always - for example, Debian-packaged python). The python shared library is
    # usually linked against the standard C library, but on some platforms (e.g., Alpine linux), this is a symbolic link
    # to the dynamic program loader binary, which our binary dependency analysis omits from the output.
    exe = sys.executable
    print(f"Python executable: {exe}")
    exe_dependencies = bindepend.get_imports(exe)
    print(f"Dependencies of Python executable: {exe_dependencies}")

    lib = bindepend.get_python_library_path()
    print(f"Python shared library: {lib}")
    lib_dependencies = bindepend.get_imports(lib)
    print(f"Dependencies of Python shared library: {lib_dependencies}")

    # At least one of these must not be empty.
    assert exe_dependencies or lib_dependencies
