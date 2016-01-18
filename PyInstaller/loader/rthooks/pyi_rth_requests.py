#-----------------------------------------------------------------------------
# Copyright (c) 2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import os
import sys

os.environ['REQUESTS_CA_BUNDLE'] = os.path.join(
    sys._MEIPASS, 'requests', 'cacert.pem')
