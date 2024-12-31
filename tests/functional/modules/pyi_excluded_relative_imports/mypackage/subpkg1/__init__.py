from mypackage import _forbidden_enabled

# Parent level 1
from .. import submod1  # noqa: F401

try:
    from .. import forbidden1  # noqa: F401
except ImportError:
    if _forbidden_enabled:
        raise

# Current level
from . import submod2  # noqa: F401

try:
    from . import forbidden2  # noqa: F401
except ImportError:
    if _forbidden_enabled:
        raise

# Sub-level 1
from .subpkg2 import submod3  # noqa: F401

try:
    from .subpkg2 import forbidden3  # noqa: F401
except ImportError:
    if _forbidden_enabled:
        raise
