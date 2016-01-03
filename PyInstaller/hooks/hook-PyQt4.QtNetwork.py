#-----------------------------------------------------------------------------
# Copyright (c) 2013-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


from PyInstaller.utils.hooks import qt4_plugins_binaries

# Network Bearer Management in Qt4 4.7+
binaries = qt4_plugins_binaries('bearer')
hiddenimports = ['sip', 'PyQt4.QtCore']
