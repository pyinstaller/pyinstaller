import os

_forbidden_enabled = os.environ.get('_FORBIDDEN_MODULES_ENABLED', '1') == '1'

# Current level
from . import submod1  # noqa: F401, E402

try:
    from . import forbidden1  # noqa: F401
except ImportError:
    if _forbidden_enabled:
        raise

# Sub-level 1
from .subpkg1 import submod2  # noqa: F401, E402

try:
    from .subpkg1 import forbidden2  # noqa: F401
except ImportError:
    if _forbidden_enabled:
        raise

# Sub-level 2
from .subpkg1.subpkg2 import submod3  # noqa: F401, E402

try:
    from .subpkg1.subpkg2 import forbidden3  # noqa: F401
except ImportError:
    if _forbidden_enabled:
        raise
