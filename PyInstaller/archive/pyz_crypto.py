#-----------------------------------------------------------------------------
# Copyright (c) 2005-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import os

BLOCK_SIZE = 16


def import_aes(module_name):
    """
    Tries to import the AES module from PyCrypto.

    PyCrypto 2.4 and 2.6 uses different name of the AES extension.
    """
    return __import__(module_name, fromlist=[module_name.split('.')[-1]])


def get_crypto_hiddenimports():
    """
    These module names are appended to the PyInstaller analysis phase.
    :return: Name of the AES module.
    """
    try:
        # The _AES.so module exists only in PyCrypto 2.6 and later. Try to import
        # that first.
        modname = 'Crypto.Cipher._AES'
        import_aes(modname)
    except ImportError:
        # Fallback to AES.so, which should be there in PyCrypto 2.4 and earlier.
        modname = 'Crypto.Cipher.AES'
        import_aes(modname)
    return modname


class PyiBlockCipher(object):
    """
    This class is used only to encrypt Python modules.
    """
    def __init__(self, key=None):
        assert type(key) is str
        if len(key) > BLOCK_SIZE:
            self.key = key[0:BLOCK_SIZE]
        else:
            self.key = key.zfill(BLOCK_SIZE)
        assert len(self.key) == BLOCK_SIZE

        # Import the right AES module.
        self._aesmod = import_aes(get_crypto_hiddenimports())

    def encrypt(self, data):
        iv = os.urandom(BLOCK_SIZE)
        return iv + self.__create_cipher(iv).encrypt(data)

    def __create_cipher(self, iv):
        # The 'BlockAlgo' class is stateful, this factory method is used to
        # re-initialize the block cipher class with each call to encrypt() and
        # decrypt().
        return self._aesmod.new(self.key.encode(), self._aesmod.MODE_CFB, iv)
