#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Verify packaging of PIL.Image. Specifically, the hidden import of FixTk
# importing tkinter is causing some problems.


from Image import fromstring


print(fromstring)
