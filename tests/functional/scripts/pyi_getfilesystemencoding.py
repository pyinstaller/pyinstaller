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

import sys

frozen_encoding = str(sys.getfilesystemencoding())

# For various OS is encoding different.
if sys.platform.startswith('win'):
    # See PEP 529 for more information.
    encoding = 'utf-8'
# On Mac OS X the value should be still the same.
elif sys.platform.startswith('darwin'):
    encoding = 'utf-8'
# On Linux and other unixes it should be usually 'utf-8'
else:
    encoding = 'utf-8'

print('Encoding expected: ' + encoding)
print('Encoding current: ' + frozen_encoding)

if not frozen_encoding == encoding:
    raise SystemExit('Frozen encoding %s is not the same as unfrozen %s.' % (frozen_encoding, encoding))
