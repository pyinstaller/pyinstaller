#-----------------------------------------------------------------------------
# Copyright (c) 2013-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
OpenGL_accelerate contais modules written in cython. This module
should speed up some functions from OpenGL module. The following
hiddenimports are not resolved by PyInstaller because OpenGL_accelerate
is compiled to native Python modules.
"""


hiddenimports = [
    'OpenGL_accelerate.wrapper',
    'OpenGL_accelerate.formathandler',
]
