
# NOTE Relative imports do not work beyond toplevel package.

# Should look for module 'relimp3c' in current directory.
from .relimp3c import c1
# Should look for module 'b1' in directory '../relimp3b' - one level up.
from ..relimp3b import b1

def getString():
  return b1.string + c1.string

