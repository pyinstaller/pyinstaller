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
import platform
from PyInstaller.utils.hooks import get_package_paths

# get path of soundfile
sfp = get_package_paths('soundfile')

# add the packaged files on OSX and Windows, libsndfile is an external dependency on Linux
path = None
if platform.system() == 'Windows':
    path = os.path.abspath(os.path.join(sfp[0], '_soundfile_data'))
elif platform.system() == 'Darwin':
    path = os.path.abspath(os.path.join(sfp[0], '_soundfile_data', 'libsndfile.dylib'))

if path is not None and os.path.exists(path):
    binaries = [(path, "_soundfile_data")]
