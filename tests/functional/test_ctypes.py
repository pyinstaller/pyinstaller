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

import ctypes
import ctypes.util
import sys

import pytest

from PyInstaller.compat import is_win
from PyInstaller.utils.tests import skipif


def test_ctypes_hooks_are_in_place(pyi_builder):
    pyi_builder.test_source(
        """
        import ctypes
        assert ctypes.CDLL.__name__ == 'PyInstallerCDLL', ctypes.CDLL
        """
    )


def test_ctypes_load_and_use_dll(pyi_builder, compiled_dylib):
    pyi_builder.test_source(
        f"""
        import os
        import sys
        import ctypes

        libname = {str(compiled_dylib.name)!r}
        libpath = os.path.join(os.path.dirname(__file__), libname)

        lib = ctypes.CDLL(libpath)

        assert lib.add_twelve(42) == 42 + 12
        """,
        # Collect the compiled shared library into top-level application directory.
        pyi_args=['--add-binary', f"{compiled_dylib}:."],
    )


# Test for error message raised by our ctypes hook when the specified shared library cannot be loaded.
def test_ctypes_cdll_unknown_dll(pyi_builder, capfd):
    with pytest.raises(pytest.fail.Exception, match="Running exe .* failed"):
        pyi_builder.test_source(
            """
            import ctypes
            ctypes.cdll.LoadLibrary('non-existing-2017')
            """
        )
    out, err = capfd.readouterr()
    assert "Failed to load dynlib/dll" in err


# Make sure we are able to load CDLL(None) -> pip does this for some reason
@skipif(is_win, reason="ctypes.CDLL(None) is not valid on Windows")
def test_ctypes_cdll_none(pyi_builder):
    pyi_builder.test_source(
        """
        import ctypes
        lib = ctypes.CDLL(None)
        assert lib is not None
        """
    )


def _monkeypatch_resolveCtypesImports(monkeypatch, compiled_dylib):
    import PyInstaller.depend.utils

    _orig_resolveCtypesImports = PyInstaller.depend.utils._resolveCtypesImports

    def mocked_resolveCtypesImports(*args, **kwargs):
        from PyInstaller.config import CONF
        old_pathex = CONF['pathex']
        CONF['pathex'].append(str(compiled_dylib))
        res = _orig_resolveCtypesImports(*args, **kwargs)
        CONF['pathex'] = old_pathex
        return res

    # Add the path to ctypes_dylib to pathex, only for _resolveCtypesImports. We can not monkeypath CONF['pathex'] here,
    # as it will be overwritten when pyi_builder is starting up. So be monkeypatch _resolveCtypesImports by a wrapper.
    monkeypatch.setattr(PyInstaller.depend.utils, "_resolveCtypesImports", mocked_resolveCtypesImports)


# Check that using `ctypes.CDLL(ctypes.util.find_library(name_literal))` ends up collecting the shared library  and
# loads the bundled copy at the run-time. This test is Linux-specific and uses system-installed shared libraries. This
# is because `ctypes.util.find_library` works with linker-like names (without "lib" prefix and ".so*" suffix and
# requires the shared library to have a valid SONAME.
@pytest.mark.linux
@pytest.mark.parametrize('libname', ['png', 'gs'])
def test_ctypes_find_library_and_cdll_on_linux(pyi_builder, libname):
    # Check that the library can be resolved via ctypes.util.find_library(), which implies its availability.
    soname = ctypes.util.find_library(libname)
    if not soname:
        pytest.skip(f"could not resolve {libname} into .so library name (library is likely not installed)")

    pyi_builder.test_source(
        f"""
        import sys
        import os
        import ctypes
        import ctypes.util

        # Try to resolve the library into soname.
        # PyInstaller's ctypes analysis can pick up only literal arguments to ctypes.util.find_library()!
        soname = ctypes.util.find_library({libname!r})
        print("Resolved soname:", soname)
        assert soname is not None, 'Could not resolve linker-like library name into .so name'

        # Load the library
        lib = ctypes.CDLL(soname)
        assert lib is not None and lib._name is not None, f'Could not load shared library {{soname}}'

        # Ensure that library with the resolved soname was in fact collected into top-level application directory.
        libfile = os.path.join(sys._MEIPASS, soname)
        assert os.path.isfile(libfile), f'Shared library {{soname}} not found in top-level application directory!'

        # Check that the library we loaded is in fact the copy from the top-level application directory. For that,
        # we need psutil.
        try:
            import psutil
        except ModuleNotFoundError:
            print("psutil not available, ending test.")

        process = psutil.Process(os.getpid())
        print("Loaded libraries:")
        for loaded_lib in process.memory_maps():
            print(f"  {{loaded_lib.path}}")

        # Find the library that matches our soname
        matching_libs = [
            loaded_lib.path for loaded_lib in process.memory_maps()
            if os.path.basename(loaded_lib.path) == soname
        ]

        print(f"Matching libraries: {{matching_libs!r}}")
        assert any(loaded_lib == libfile for loaded_lib in matching_libs), f'Bundled copy of {{soname}} not loaded!'
        """
    )


#-- Generate test-cases for the different types of ctypes objects.
_ctypes_parameters = []
_ctypes_ids = []
for prefix in ('', 'ctypes.'):
    for funcname in ('CDLL', 'PyDLL', 'WinDLL', 'OleDLL', 'cdll.LoadLibrary'):
        _ctypes_ids.append(prefix + funcname)
        params = (prefix + funcname, _ctypes_ids[-1])
        if funcname in ("WinDLL", "OleDLL"):
            # WinDLL, OleDLL only work on Windows.
            params = pytest.param(*params, marks=pytest.mark.win32)
        _ctypes_parameters.append(params)


@pytest.mark.parametrize("funcname,test_id", _ctypes_parameters, ids=_ctypes_ids)
def test_ctypes_bindings(pyi_builder, monkeypatch, compiled_dylib, funcname, test_id):
    # Evaluate the soname here, so the test-code contains a constant. We want the name of the dynamically-loaded library
    # only, not its path. See discussion in https://github.com/pyinstaller/pyinstaller/pull/1478#issuecomment-139622994.
    soname = compiled_dylib.name

    # Patch _resolveCtypesImports tp extend search path with the parent directory of the compiled shared library.
    _monkeypatch_resolveCtypesImports(monkeypatch, compiled_dylib.parent)

    pyi_builder.test_source(
        f"""
        import os
        import sys

        # Both imports allow us to prefixed and non-prefixed funcname.
        import ctypes
        from ctypes import *

        # Load the library.
        lib = {funcname}({soname!r})
        print(f"Loaded library handle: {{lib}}")

        libfile = os.path.join(sys._MEIPASS, {soname!r})
        assert os.path.isfile(libfile), f'Shared library {{soname}} not found in top-level application directory!'

        # NOTE: since we are using our own compiled test library, we do not need to explicitly check that the bundled
        # copy is loaded.
        """,
        test_id=test_id,
    )


@pytest.mark.parametrize("funcname,test_id", _ctypes_parameters, ids=_ctypes_ids)
def test_ctypes_bindings_in_function(pyi_builder, monkeypatch, compiled_dylib, funcname, test_id):
    # This is much like test_ctypes_bindings except that the ctypes calls are in a function. See issue #1620.
    soname = compiled_dylib.name

    _monkeypatch_resolveCtypesImports(monkeypatch, compiled_dylib.parent)

    pyi_builder.test_source(
        f"""
        import os
        import sys

        # Both imports allow us to prefixed and non-prefixed funcname.
        import ctypes
        from ctypes import *

        # Load the library.
        def f():
            def g():
                lib = {funcname}({soname!r})
                return lib
            return g()

        lib = f()
        print(f"Loaded library handle: {{lib}}")

        libfile = os.path.join(sys._MEIPASS, {soname!r})
        assert os.path.isfile(libfile), f'Shared library {{soname}} not found in top-level application directory!'

        # NOTE: since we are using our own compiled test library, we do not need to explicitly check that the bundled
        # copy is loaded.
        """,
        test_id=test_id,
    )


def test_ctypes_cdll_builtin_extension(pyi_builder):
    # Take a built-in that is provided as an extension
    builtin_ext = '_sha256'
    if builtin_ext in sys.builtin_module_names:
        # On Windows, built-ins do not seem to be extensions
        pytest.skip(f"{builtin_ext} is a built-in module without extension.")

    pyi_builder.test_source(
        f"""
        import ctypes
        import importlib.machinery

        # Try to load CDLL with all possible extension suffices; this should fail in all cases, as built-in extensions
        # should not be in the ctypes' search path.
        builtin_ext = {builtin_ext!r}
        for suffix in importlib.machinery.EXTENSION_SUFFIXES:
            try:
                lib = ctypes.CDLL(builtin_ext + suffix)
            except OSError:
                lib = None
            assert lib is None, "Built-in extension picked up by ctypes.CDLL!"
        """
    )
