#-----------------------------------------------------------------------------
# Copyright (c) 2013-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

"""
accessible_output2: http://hg.q-continuum.net/accessible_output2
"""

import os.path
import accessible_output2 as _accessible_output2

_dir = os.path.dirname(_accessible_output2.__file__)

binaries = [(os.path.join(_dir, 'lib'), os.path.join('accessible_output2', 'lib'))]
