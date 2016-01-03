#-----------------------------------------------------------------------------
# Copyright (c) 2005-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import sys
import os

import PIL.Image


# Disable "leaking" the installed version.
PIL.Image.__file__ = '/'


# Convert tiff to png.
basedir = sys._MEIPASS
im = PIL.Image.open(os.path.join(basedir, "tinysample.tiff"))
im.save(os.path.join(basedir, "tinysample.png"))
