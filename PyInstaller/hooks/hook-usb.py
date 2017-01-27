#-----------------------------------------------------------------------------
# Copyright (c) 2013-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import ctypes.util
import os
import usb.core
import usb.backend

from PyInstaller.depend.utils import _resolveCtypesImports
from PyInstaller.compat import is_cygwin
from PyInstaller.utils.hooks import logger


# Include glob for library lookup in run-time hook.
hiddenimports = ['glob']

# https://github.com/walac/pyusb/blob/master/docs/faq.rst
# https://github.com/walac/pyusb/blob/master/docs/tutorial.rst

binaries=[]

# first try to use pyusb library locator
try:
    # get the backend symbols before find
    pyusb_backend_dir = set(dir(usb.backend))

    # perform find, which will load a usb library if found
    usb.core.find()

    # get the backend symbols which have been added (loaded)
    backends = set(dir(usb.backend)) - pyusb_backend_dir

    # for each of the loaded backends, see if they have a library
    binaries = []
    for usblib in [getattr(usb.backend, be)._lib for be in backends]:
        if usblib is not None:
            binaries = [(usblib._name, '')]

except (ValueError, usb.core.USBError) as exc:
    logger.warning("%s", exc)


# if nothing found, try to use our custom mechanism
if not binaries:
    # Try to resolve your libusb libraries in the following order:
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

    for candidate in libusb_candidates:
        libname = ctypes.util.find_library(candidate)
        if libname is not None:
            break

    if libname is not None:
        # Use basename here because Python returns full library path
        # on Mac OSX when using ctypes.util.find_library.
        bins = [os.path.basename(libname)]
        binaries = _resolveCtypesImports(bins)
    elif is_cygwin:
        bins = ['cygusb-1.0-0.dll', 'cygusb0.dll']
        binaries = _resolveCtypesImports(bins)[:1] # use only the first one
    else:
        binaries = []

    if binaries:
        # `_resolveCtypesImports` returns a 3-tuple, but `binaries` are only
        # 2-tuples, so remove the last element:
        assert len(binaries[0]) == 3
        binaries = [(binaries[0][1], '')]
