#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Forward to shared code for PIL. PIL can be imported either as a top-level package
# (from PIL import Image), or not (import Image), because it installs a
# PIL.pth.
from PyInstaller.hooks.shared_PIL_Image import *
