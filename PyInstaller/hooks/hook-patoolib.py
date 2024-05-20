#-----------------------------------------------------------------------------
# Copyright (c) 2017-2024, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
patoolib uses importlib and pyinstaller doesn't find it and add it to the list of needed modules
"""

from PyInstaller.utils.hooks import collect_submodules
hiddenimports = collect_submodules('patoolib.programs')
