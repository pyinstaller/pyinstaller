#-----------------------------------------------------------------------------
# Copyright (c) 2015-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import os
import sys

os.environ['GI_TYPELIB_PATH'] = os.path.join(sys._MEIPASS, 'gi_typelibs')
