#-----------------------------------------------------------------------------
# Copyright (c) 2016-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

"""
pysoundfile:
https://github.com/bastibe/SoundFile
"""

import os

from PyInstaller.compat import is_win, is_darwin
from PyInstaller.utils.hooks import get_package_paths

# get path of soundfile
sfp = get_package_paths('soundfile')

# add binaries packaged by soundfile on OSX and Windows
# an external dependency (libsndfile) is used on GNU/Linux
path = None
if is_win:
    path = os.path.join(sfp[0], '_soundfile_data')
elif is_darwin:
    path = os.path.join(sfp[0], '_soundfile_data', 'libsndfile.dylib')

if path is not None and os.path.exists(path):
    binaries = [(path, "_soundfile_data")]
