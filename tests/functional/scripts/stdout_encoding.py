#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import sys
# Get the expected stdout/stderr encoding for this platform.
from pyi_testmod_stdxxx_encoding import encoding

frozen_encoding = str(sys.stdout.encoding)

print('Encoding expected: ' + encoding)
print('Encoding current: ' + frozen_encoding)

if not frozen_encoding == encoding:
    raise SystemExit('Frozen encoding %s is not the same as unfrozen %s.' %
                     (frozen_encoding, encoding))

