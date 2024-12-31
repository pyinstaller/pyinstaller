from mypackage import _forbidden_enabled

# Current level
try:
    from . import forbidden1  # noqa: F401
except ImportError:
    if _forbidden_enabled:
        raise

# Sub-level 1
try:
    from .subpkg1 import forbidden2  # noqa: F401
except ImportError:
    if _forbidden_enabled:
        raise

# Sub-level 2
try:
    from .subpkg1.subpkg2 import forbidden3  # noqa: F401
except ImportError:
    if _forbidden_enabled:
        raise
