#-----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import sys


frozen_encoding = str(sys.getfilesystemencoding())


# For various OS is encoding different.
# On Windows it should be still mbcs up to Python 3.5
if sys.platform.startswith('win'):
    encoding = 'mbcs'
    if sys.version_info >= (3, 6):
        # See PEP 529 for more information.
        encoding = 'utf-8'
# On Mac OS X the value should be still the same.
elif sys.platform.startswith('darwin'):
    encoding = 'utf-8'
# On Linux and other unixes it should be usually 'utf-8'
else:
    # For Python 2 the bootloader sets encoding explicitly.
    # It should be 'UTF-8'.
    if sys.version_info[0] == 2:
        encoding = 'UTF-8'
    # Python 3 reports encoding 'utf-8'.
    else:
        encoding = 'utf-8'


print('Encoding expected: ' + encoding)
print('Encoding current: ' + frozen_encoding)


if not frozen_encoding == encoding:
    raise SystemExit('Frozen encoding %s is not the same as unfrozen %s.' %
                     (frozen_encoding, encoding))
