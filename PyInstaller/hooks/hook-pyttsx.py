#-----------------------------------------------------------------------------
# Copyright (c) 2013-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
pyttsx imports drivers module based on specific platform.
Found at http://mrmekon.tumblr.com/post/5272210442/pyinstaller-and-pyttsx
"""


hiddenimports = [
    'drivers',
    'drivers.dummy',
    'drivers.espeak',
    'drivers.nsss',
    'drivers.sapi5',
]
