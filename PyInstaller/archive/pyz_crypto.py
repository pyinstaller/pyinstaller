#-----------------------------------------------------------------------------
# Copyright (c) 2005-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import os

BLOCK_SIZE = 16

class PyiBlockCipher(object):
    """
    This class is used only to encrypt Python modules.
    """
    def __init__(self, key=None):
        import pyaes
        self._aes = pyaes
        assert type(key) is str
        if len(key) > BLOCK_SIZE:
            self.key = key[0:BLOCK_SIZE]
        else:
            self.key = key.zfill(BLOCK_SIZE)
        assert len(self.key) == BLOCK_SIZE

    def encrypt(self, data):
        iv = os.urandom(BLOCK_SIZE)
        return iv + self.__create_cipher(iv).encrypt(data)

    def __create_cipher(self, iv):
        # The 'AESModeOfOperationCFB' class is stateful, this factory method is used to
        # re-initialize the block cipher class with each call to encrypt() and decrypt().
        return self._aes.AESModeOfOperationCFB(self.key.encode(), iv=iv)
