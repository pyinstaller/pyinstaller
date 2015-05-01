#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import os
import sys

babel_root = os.path.join(sys._MEIPASS, "babel")

import babel.localedata
import babel.core
babel.localedata._dirname = os.path.join(babel_root, "localedata")

filename = os.path.join(babel_root, 'global.dat')
fileobj = open(filename, 'rb')
try:
    babel.core._global_data = babel.core.pickle.load(fileobj)
finally:
    fileobj.close()
