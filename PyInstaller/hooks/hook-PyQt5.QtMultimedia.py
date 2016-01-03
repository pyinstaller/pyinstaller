#-----------------------------------------------------------------------------
# Copyright (c) 2013-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# QtMultimedia tries to pull in QtNetwork

hiddenimports = [ 'PyQt5.QtNetwork' ]

# QtMultimedia needs some plugins

from PyInstaller.utils.hooks import qt5_plugins_binaries

binaries = []
binaries.extend( qt5_plugins_binaries( 'audio' ) )
binaries.extend( qt5_plugins_binaries( 'mediaservice' ) )
