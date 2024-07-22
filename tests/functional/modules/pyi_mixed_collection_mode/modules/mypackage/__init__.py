# Two modules; one is collected into PYZ archive (and is thus handled by PyInstaller's frozen importer); the other is
# collected as source .py file only (forced by module_collection_mode setting in the accompanying hook), and is thus
# handled by python's own `_frozen_importlib_external.PathFinder`. Both, however, need to be importable in the frozen
# application. In other words, PyInstaller's frozen importer and python's `_frozen_importlib_external.PathFinder` must
# complement, and not exclude, each other.
#
# NOTE: same scenario could be achieved with a package that contains a pure-python module (collected into PYZ by
# default) and a binary extension module (always collected as a file); however, test setup is more practical with two
# (empty) pure-python modules and manipulated collection mode.
from . import a  # noqa: F401
from . import b  # noqa: F401
