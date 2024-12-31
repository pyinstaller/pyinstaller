from mypackage import _forbidden_enabled

# Parent level 2
from ... import submod1  # noqa: F401

try:
    from ... import forbidden1  # noqa: F401
except ImportError:
    if _forbidden_enabled:
        raise

# Parent level 1
from .. import submod2  # noqa: F401

try:
    from .. import forbidden2  # noqa: F401
except ImportError:
    if _forbidden_enabled:
        raise

# Current level
from . import submod3  # noqa: F401

try:
    from . import forbidden3  # noqa: F401
except ImportError:
    if _forbidden_enabled:
        raise
