#-----------------------------------------------------------------------------
# Copyright (c) 2013-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Some modules use the old-style import: explicitly include 
the new module when the old one is referenced.
"""


hiddenimports = ["email.mime.text", "email.mime.multipart"]
