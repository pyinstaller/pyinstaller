#-----------------------------------------------------------------------------
# Copyright (c) 2013-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
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
