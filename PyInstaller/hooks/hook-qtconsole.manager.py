#-----------------------------------------------------------------------------
# Copyright (c) 2005-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

"""
Hook for qtconsole library: https://github.com/jupyter/qtconsole
qtconsole provides a qt based terminal for the iPython kernel system.

See the list of kernels here:
https://github.com/jupyter/jupyter/wiki/Jupyter-kernels
"""

hiddenimports = [
    "qtconsole.client"
]
