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
#
# Tests for stdlib `inspect` module.

import pathlib

import pytest

# Directory with testing modules used in some tests.
_MODULES_DIR = pathlib.Path(__file__).parent / 'modules'


def _patch_collection_mode(monkeypatch, module_name):
    # Patch Analysis to set module_collection_mode for specified package/module.
    import PyInstaller.building.build_main

    class _Analysis(PyInstaller.building.build_main.Analysis):
        def __init__(self, *args, **kwargs):
            kwargs['module_collection_mode'] = {
                module_name: 'pyz+py',
            }
            super().__init__(*args, **kwargs)

    monkeypatch.setattr('PyInstaller.building.build_main.Analysis', _Analysis)


# Test that we can retrieve source for a module that was collected both into PYZ archive and as a source .py file.
@pytest.mark.parametrize('module_name', ['mypackage', 'mypackage.mod_a'], ids=['package', 'submodule'])
def test_inspect_getsource(pyi_builder, module_name, monkeypatch):
    pathex = _MODULES_DIR / 'pyi_inspect_getsource'
    _patch_collection_mode(monkeypatch, 'mypackage')
    pyi_builder.test_source(
        f"""
        import inspect

        import {module_name}

        # Retrieve source via module instance.
        source = inspect.getsource({module_name})
        print(source)

        # Check that the source starts with expected comment
        EXPECTED_COMMENT = "# {module_name}: "
        if not source.startswith(EXPECTED_COMMENT):
            raise ValueError(f"Source does not start with expected comment: {{EXPECTED_COMMENT}}")
        """,
        pyi_args=['--paths', str(pathex)],
    )


def test_inspect_getsource_class_from_base_library_module(pyi_builder, monkeypatch):
    _patch_collection_mode(monkeypatch, 'enum')
    pyi_builder.test_source(
        """
        import sys
        import os
        import enum
        import inspect

        # Ensure that module is collected in `base_library.zip`; normalize separators before comparison.
        BASE_LIBRARY_ZIP = os.path.normpath(os.path.join(sys._MEIPASS, 'base_library.zip'))
        if not enum.__file__.startswith(BASE_LIBRARY_ZIP):
            raise ValueError(f"The 'enum' module is not collected in base_library.zip: {enum.__file__}")

        # Retrieve source via class (enum.Enum)
        source = inspect.getsource(enum.Enum)
        print(source)
        """
    )


def test_inspect_getsource_class_method_from_base_library_module(pyi_builder, monkeypatch):
    _patch_collection_mode(monkeypatch, 'enum')
    pyi_builder.test_source(
        """
        import sys
        import os
        import enum
        import inspect

        # Ensure that module is collected in `base_library.zip`; normalize separators before comparison.
        BASE_LIBRARY_ZIP = os.path.normpath(os.path.join(sys._MEIPASS, 'base_library.zip'))
        if not enum.__file__.startswith(BASE_LIBRARY_ZIP):
            raise ValueError(f"The 'enum' module is not collected in base_library.zip: {enum.__file__}")

        # Retrieve source via class method (enum.Enum.__new__)
        source = inspect.getsource(enum.Enum.__new__)
        print(source)
        """
    )


# Similar to `test_inspect_getsource`, except that we are retrieving source for a function within the module.
def test_inspect_getsource_function(pyi_builder, monkeypatch):
    pathex = _MODULES_DIR / 'pyi_inspect_getsource'
    _patch_collection_mode(monkeypatch, 'mypackage')
    pyi_builder.test_source(
        """
        import inspect

        from mypackage.mod_b import test_function

        # Retrieve source for function.
        source = inspect.getsource(test_function)
        print(source)

        # Check that the source starts with function definition
        EXPECTED_START = "def test_function():"
        if not source.startswith(EXPECTED_START):
            raise ValueError(f"Source does not start with function definition: {EXPECTED_START}")

        # Check that the comment is preset.
        EXPECTED_COMMENT = "# A comment."
        if EXPECTED_COMMENT not in source:
            raise ValueError(f"Source does not contain expected comment: {EXPECTED_COMMENT}")
        """,
        pyi_args=['--paths', str(pathex)],
    )


# Test inspect.getmodule() on stack-frames obtained by inspect.stack(). Reproduces the issue reported by #5963 while
# expanding the test to cover a package and its submodule in addition to the __main__ module.
def test_inspect_getmodule_from_stackframes(pyi_builder):
    pathex = _MODULES_DIR / 'pyi_inspect_getmodule_from_stackframes'
    # NOTE: run_from_path MUST be True, otherwise cwd + rel_path coincides with sys._MEIPASS + rel_path and masks the
    # path resolving issue in onedir builds.
    pyi_builder.test_source(
        """
        import helper_package

        # helper_package.test_call_chain() calls eponymous function in helper_package.helper_module, which in turn uses
        # inspect.stack() and inspect.getmodule() to obtain list of modules involved in the chain call.
        modules = helper_package.test_call_chain()

        # Expected call chain
        expected_module_names = [
            'helper_package.helper_module',
            'helper_package',
            '__main__'
        ]

        # All modules must have been resolved
        assert not any(module is None for module in modules)

        # Verify module names
        module_names = [module.__name__ for module in modules]
        assert module_names == expected_module_names
        """,
        pyi_args=['--paths', str(pathex)],
        run_from_path=True
    )


# Test the robustness of `inspect` run-time hook w.r.t. to the issue #7642.
#
# If our run-time hook imports a module in the global namespace and attempts to use this module in a function that
# might get called later on in the program (e.g., a function override or registered callback function), we are at the
# mercy of user's program, which might re-bind the module's name to something else (variable, function), leading to
# an error.
#
# This particular test will raise:
# ```
# Traceback (most recent call last):
#  File "test_source.py", line 17, in <module>
#  File "test_source.py", line 14, in some_interactive_debugger_function
#  File "inspect.py", line 1755, in stack
#  File "inspect.py", line 1730, in getouterframes
#  File "inspect.py", line 1688, in getframeinfo
#  File "PyInstaller/hooks/rthooks/pyi_rth_inspect.py", line 22, in _pyi_getsourcefile
# AttributeError: 'function' object has no attribute 'getfile'
# ```
def test_inspect_rthook_robustness(pyi_builder):
    pyi_builder.test_source(
        """
        # A custom function in global namespace that happens to have name clash with `inspect` module.
        def inspect(something):
            print(f"Inspecting {something}: type is {type(something)}")


        # A call to `inspect.stack` function somewhere deep in an interactive debugger framework.
        # This eventually ends up calling our `_pyi_getsourcefile` override in the `inspect` run-time hook. The
        # override calls `inspect.getfile`; if the run-time hook imported `inspect` in a global namespace, the
        # name at this point is bound the the custom function that program defined, leading to an error.
        def some_interactive_debugger_function():
            import inspect
            print(f"Current stack: {inspect.stack()}")


        some_interactive_debugger_function()
        """
    )
