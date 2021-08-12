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
import codecs

# Get the expected stdout/stderr encoding for this platform.
from pyi_testmod_gettemp import gettemp

with open(gettemp("stderr_encoding.build")) as f:
    encoding = f.read()
frozen_encoding = sys.stderr.encoding

# Normalize encoding names - "UTF-8" should be the same as "utf8".
encoding = codecs.lookup(encoding).name
frozen_encoding = codecs.lookup(frozen_encoding).name

print('Encoding expected:', encoding)
print('Encoding current:', frozen_encoding)

if frozen_encoding != encoding:
    raise SystemExit('Frozen encoding %s is not the same as unfrozen %s.' % (frozen_encoding, encoding))
