#-----------------------------------------------------------------------------
# Copyright (c) 2005-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
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
