#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
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


if hasattr(sys, 'frozen'):
    basedir = sys._MEIPASS
else:
    basedir = os.path.dirname(__file__)


im = PIL.Image.open(os.path.join(basedir, "tinysample.tiff"))
im.save(os.path.join(basedir, "tinysample.png"))
