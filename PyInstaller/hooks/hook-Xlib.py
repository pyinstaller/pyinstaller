#-----------------------------------------------------------------------------
# Copyright (c) 2014, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import sys

from PyInstaller import is_unix

import hookutils

if is_unix:
    hiddenimports = hookutils.collect_submodules('Xlib')
