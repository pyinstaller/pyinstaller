#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


hiddenimports = ['sip', 'PyQt4.QtCore', 'PyQt4._qt']

from PyInstaller.hooks.hookutils import qt4_plugins_binaries


def hook(mod):
    # TODO fix this hook to use attribute 'binaries'.
    mod.pyinstaller_binaries.extend(qt4_plugins_binaries('accessible'))
    mod.pyinstaller_binaries.extend(qt4_plugins_binaries('iconengines'))
    mod.pyinstaller_binaries.extend(qt4_plugins_binaries('imageformats'))
    mod.pyinstaller_binaries.extend(qt4_plugins_binaries('inputmethods'))
    mod.pyinstaller_binaries.extend(qt4_plugins_binaries('graphicssystems'))
    return mod
