#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import sys
import codecs


# Get the expected stdout/stderr encoding for this platform.
from pyi_testmod_gettemp import gettemp

with open(gettemp("stdout_encoding.build")) as f:
    encoding = f.read()
frozen_encoding = str(sys.stdout.encoding)

# Skip normalizing if encoding is None. This happens for Python 2.
if not encoding == 'None' and not frozen_encoding == 'None':
    # Normalize encoding names - "UTF-8" should be the same as "utf8"
    encoding = codecs.lookup(encoding).name
    frozen_encoding = codecs.lookup(frozen_encoding).name


print('Encoding expected: ' + encoding)
print('Encoding current: ' + frozen_encoding)

if not frozen_encoding == encoding:
    raise SystemExit('Frozen encoding %s is not the same as unfrozen %s.' %
                     (frozen_encoding, encoding))

