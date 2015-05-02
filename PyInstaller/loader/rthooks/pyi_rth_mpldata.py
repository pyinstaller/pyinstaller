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

meipass_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
os.environ["MATPLOTLIBDATA"] = os.path.join(meipass_dir, "mpl-data")
