#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import pyi_crypto
import pyimod00_crypto_key


assert type(pyimod00_crypto_key.key) is str
# The test runner uses 'test_key' as key.
assert pyimod00_crypto_key.key == 'test_key'.zfill(pyi_crypto.BLOCK_SIZE)
