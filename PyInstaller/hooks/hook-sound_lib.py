"""
sound_lib: http://hg.q-continuum.net/sound_lib
"""

import os.path
import sound_lib as _sound_lib

_dir = os.path.dirname(_sound_lib.__file__)

binaries = [(os.path.join(_dir, 'lib'), os.path.join('sound_lib', 'lib'))]
