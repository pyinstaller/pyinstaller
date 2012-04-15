#
# Copyright (C) 2012, Chien-An "Zero" Cho
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA


import ctypes.util
import os

from PyInstaller.depend.utils import _resolveCtypesImports
from PyInstaller.compat import is_cygwin


# Include glob for library lookup in run-time hook.
hiddenimports = ['glob']


# This method will try to resolve your libusb libraries in the
# following orders:
#
#   libusb-1.0, libusb-0.1, openusb
#
# NOTE: Mind updating run-time hook when adding further libs.
libusb_candidates = (
    # libusb10
    'usb-1.0', 'usb', 'libusb-1.0',
    # libusb01
    'usb-0.1', 'libusb0',
    # openusb
    'openusb',
)


def hook(mod):
    for candidate in libusb_candidates:
        libname = ctypes.util.find_library(candidate)
        if libname is not None:
            break

    if libname is not None:
        # Use basename here because Python returns full library path
        # on Mac OSX when using ctypes.util.find_library.
        bins = [os.path.basename(libname)]
        mod.binaries.extend(_resolveCtypesImports(bins))
    elif is_cygwin:
        bins = ['cygusb-1.0-0.dll', 'cygusb0.dll']
        mod.binaries.extend(_resolveCtypesImports(bins)[0:1])

    return mod
