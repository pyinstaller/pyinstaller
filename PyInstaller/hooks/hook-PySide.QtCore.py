#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


hiddenimports = []

from PyInstaller.hooks.hookutils import qt4_plugins_binaries

ns = "PySide"

def hook(mod):
    # TODO fix this hook to use attribute 'binaries'.
    mod.pyinstaller_binaries.extend(qt4_plugins_binaries('codecs', ns=ns))
    return mod
