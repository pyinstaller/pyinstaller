
from __future__ import absolute_import

from . import relimp2 as upper
from . relimp import relimp2 as lower

if upper.__name__ == lower.__name__:
    raise SystemExit("Imported the same module")

if upper.__file__ == lower.__file__:
    raise SystemExit("Imported the same file")
