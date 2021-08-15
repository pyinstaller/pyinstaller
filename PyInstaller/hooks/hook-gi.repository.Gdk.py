#-----------------------------------------------------------------------------
# Copyright (c) 2005-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""
Import hook for PyGObject https://wiki.gnome.org/PyGObject
"""

from PyInstaller.utils.hooks.gi import get_gi_typelibs

binaries, datas, hiddenimports = get_gi_typelibs('Gdk', '3.0')
hiddenimports += ['gi._gi_cairo', 'gi.repository.cairo']
