#-----------------------------------------------------------------------------
# Copyright (c) 2005-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from pyimod00_crypto_key import key
from pyimod02_archive import CRYPT_BLOCK_SIZE

# Issue 1663: Crypto feature caused issues when using PyCrypto module.
import Crypto.Cipher.AES

assert type(key) is str
# The test runner uses 'test_key' as key.
assert key == 'test_key'.zfill(CRYPT_BLOCK_SIZE)
