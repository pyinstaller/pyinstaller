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

# Directory with testing modules used in some tests.
_MODULES_DIR = pathlib.Path(__file__).parent / 'modules'


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
