"""
Testing utilities
"""
import sys
import os
import importlib


def clear_sys_modules(test_path):
    to_remove = []
    for mod in sys.modules:
        if (
            hasattr(sys.modules[mod], "__file__")
            and sys.modules[mod].__file__ is not None
            and sys.modules[mod].__file__.startswith(os.fspath(test_path))
        ):
            to_remove.append(mod)
    for mod in to_remove:
        del sys.modules[mod]

    importlib.invalidate_caches()
