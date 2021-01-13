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

from PyInstaller.compat import modname_tkinter


# PIL's SpiderImagePlugin features a tkPhotoImage() method which imports
# ImageTk (and thus brings the whole Tcl/Tk library in).
# Assume that if people are really using tkinter in their application, they
# will also import it directly.
excludedimports = [modname_tkinter, 'FixTk']
