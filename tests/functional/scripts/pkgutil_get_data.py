#-----------------------------------------------------------------------------
# Copyright (c) 2013-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import pkgutil

import pkg3  # noqa: F401

expected_data = 'This is data text for testing the packaging module data.'.encode('ascii')

data = pkgutil.get_data('pkg3', 'sample-data.txt')
if not data:
    raise SystemExit('Error: Could not read data with pkgutil.get_data().')

if data.strip() != expected_data:
    raise SystemExit('Error: Read data is wrong: %r' % data)
print('Okay: Resource data read.')
