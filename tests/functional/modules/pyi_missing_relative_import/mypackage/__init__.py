# Different forms of relative-import for an optional sub-module. While the said sub-module does not exist, an
# unrelated eponymous top-level module does - and these import attempts should *NOT* trigger its collection!
try:
    from . import myotherpackage  # noqa: F401
except ImportError:
    pass

try:
    from .myotherpackage import something  # noqa: F401
except ImportError:
    pass
