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

import PyInstaller.utils.hooks as hookutils

hiddenimports = hookutils.collect_submodules('Xlib')
