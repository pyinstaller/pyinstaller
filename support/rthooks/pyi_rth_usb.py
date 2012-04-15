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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA


import ctypes
import glob
import os
import sys
import usb.backend.libusb10 as libusb10
import usb.backend.libusb01 as libusb01
import usb.backend.openusb as openusb


def get_load_func(type, candidates):
    def _load_library():
        exec_path = sys._MEIPASS

        l = None
        for candidate in candidates:
            # Do linker's path lookup work to force load bundled copy.
            if os.name == 'posix' and sys.platform == 'darwin':
                libs = glob.glob("%s/%s*.dylib*" % (exec_path, candidate))
            elif sys.platform == 'win32' or sys.platform == 'cygwin':
                libs = glob.glob("%s\\%s*.dll" % (exec_path, candidate))
            else:
                libs = glob.glob("%s/%s*.so*" % (exec_path, candidate))
            for libname in libs:
                try:
                    # NOTE: libusb01 is using CDLL under win32.
                    # (see usb.backends.libusb01)
                    if sys.platform == 'win32' and type != 'libusb01':
                        l = ctypes.WinDLL(libname)
                    else:
                        l = ctypes.CDLL(libname)
                    if l is not None:
                        break
                except:
                    l = None
            if l is not None:
                break
        else:
            raise OSError('USB library could not be found')

        if type == 'libusb10':
            if not hasattr(l, 'libusb_init'):
                raise OSError('USB library could not be found')
        return l
    return _load_library


# NOTE: Need to keep in sync with future PyUSB updates.
if sys.platform == 'cygwin':
    libusb10._load_library = get_load_func('libusb10', ('cygusb-1.0', ))
    libusb01._load_library = get_load_func('libusb01', ('cygusb0', ))
    openusb._load_library = get_load_func('openusb', ('openusb', ))
else:
    libusb10._load_library = get_load_func('libusb10', ('usb-1.0', 'libusb-1.0', 'usb'))
    libusb01._load_library = get_load_func('libusb01', ('usb-0.1', 'usb', 'libusb0'))
    openusb._load_library = get_load_func('openusb', ('openusb', ))
