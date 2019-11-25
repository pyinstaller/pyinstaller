#-----------------------------------------------------------------------------
# Copyright (c) 2016-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

"""
enzyme:
https://github.com/Diaoul/enzyme
"""

import os
from PyInstaller.utils.hooks import get_package_paths

# get path of enzyme
ep = get_package_paths('enzyme')

# add the data
data = os.path.join(ep[1], 'parsers', 'ebml', 'specs', 'matroska.xml')
datas = [(data, "enzyme/parsers/ebml/specs")]
