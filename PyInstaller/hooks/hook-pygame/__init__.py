#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Hook for pygame._view, required for develop releases between
2011-02-08 and 2011-08-31, including prebuilt-pygame1.9.2a0
"""


hiddenimports = ['pygame._view']
