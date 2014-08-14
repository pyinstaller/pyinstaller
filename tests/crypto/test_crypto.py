#-----------------------------------------------------------------------------
# Copyright (c) 2014, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import pyi_crypto
import pyi_crypto_key

assert type(pyi_crypto_key.key) is str
assert pyi_crypto_key.key == 'test_key'.zfill(pyi_crypto.BLOCK_SIZE)  # The test runner uses 'test_key' as key.
