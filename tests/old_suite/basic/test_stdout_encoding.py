#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import sys


frozen_encoding = str(sys.stdout.encoding)


# For various OS encoding is different.
# On Windows it should be still cp850.  ## FIXME: Is this correct???  I don't have Windows!
# On Linux, MAC OS X, and other unixes it should be mostly 'UTF-8'.
encoding = 'cp850' if sys.platform.startswith('win') else 'UTF-8'


print('Encoding expected: ' + encoding)
print('Encoding current: ' + frozen_encoding)


if not frozen_encoding == encoding:
    raise SystemExit('Frozen encoding %s is not the same as unfrozen %s.' %
                     (frozen_encoding, encoding))
