
from __future__ import absolute_import

name = 'relimp.relimp.relimp2'

from . import relimp3
assert relimp3.name == 'relimp.relimp.relimp3'

from .. import relimp
assert relimp.name == 'relimp.relimp'

import relimp
assert relimp.name == 'relimp'

import relimp.relimp2
assert relimp.relimp2.name == 'relimp.relimp2'

# While this seams to work when running Python, it is wrong:
#  .relimp should be a sibling of this package
#from .relimp import relimp2
#assert relimp2.name == 'relimp.relimp2'

