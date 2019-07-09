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
from PyInstaller.utils.hooks import get_package_paths

# get path of soundfile
sfp = get_package_paths('soundfile')

# add the binaries
bins = os.path.join(sfp[0], "_soundfile_data")
binaries = [(bins, "_soundfile_data")]
