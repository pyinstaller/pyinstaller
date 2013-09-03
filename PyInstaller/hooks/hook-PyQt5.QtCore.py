#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


hiddenimports = ['sip']

from PyInstaller.hooks.hookutils import qt5_plugins_binaries


def hook(mod):
    mod.binaries.extend(qt5_plugins_binaries('codecs'))
    return mod
