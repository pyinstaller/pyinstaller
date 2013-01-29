#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import PyInstaller.hooks.hookutils


# If the user imports setuparg1, we just set an attribute
# in PyInstaller.hooks.hookutils that allows us to later
# find out about this.
PyInstaller.hooks.hookutils.wxpubsub = 'arg1'
