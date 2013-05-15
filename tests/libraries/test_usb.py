#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import usb.core

# Detect usb devices.
devices = usb.core.find(find_all = True)

if not devices:
    raise SystemExit('No USB device found.')
