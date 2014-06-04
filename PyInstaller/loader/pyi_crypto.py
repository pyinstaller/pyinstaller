#-----------------------------------------------------------------------------
# Copyright (c) 2014, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


BLOCK_SIZE = 16


def import_aes(module_name):
    """Tries to import the AES module from PyCrypto."""
    try:
        # Easy way: this should work at build time.
        return __import__(module_name, fromlist=[module_name.split('.')[-1]])
    except ImportError:
        # Not-so-easy way: at bootstrap time we have to load the module from the
        # temporary directory in a manner similar to
        # pyi_importers.CExtensionImporter.
        from pyi_importers import CExtensionImporter

        # NOTE: We _must_ call find_module first.
        mod = CExtensionImporter().find_module(module_name)

        if not mod:
            raise ImportError(module_name)

        return mod.load_module(module_name)


try:
    # The _AES.so module exists only in PyCrypto 2.6 and later. Try to import
    # that first.
    modname = 'Crypto.Cipher._AES'

    AES = import_aes('Crypto.Cipher._AES')
    HIDDENIMPORT = modname
except ImportError:
    # Fallback to AES.so, which should be there in PyCrypto 2.4 and earlier.
    modname = 'Crypto.Cipher.AES'

    AES = import_aes(modname)
    HIDDENIMPORT = modname


class PyiBlockCipher(object):
    def __init__(self, key=None):
        if key is None:
            # At build-type the key is given to us from inside the spec file, at
            # bootstrap-time, we must look for it ourselves by trying to import
            # the generated 'pyi_crypto_key' module.
            import pyi_crypto_key

            key = pyi_crypto_key.key

        assert type(key) is str

        if len(key) > BLOCK_SIZE:
            self.key = key[0:BLOCK_SIZE]
        else:
            self.key = key.zfill(BLOCK_SIZE)

        assert len(self.key) == BLOCK_SIZE

        # Import os.urandom locally since we need it only at build time (i.e.:
        # when calling self.encrypt(), to provide the IV). We can't regularly
        # import 'os' just yet because pyi_importers.FrozenImporter hasn't been
        # installed as import hook during the bootstrap process, thus, the
        # import would fail.
        try:
            self.urandom = __import__('os').urandom
        except ImportError:
            pass

    def encrypt(self, data):
        # NOTE: This call will fail at bootstrap-time. See note in the
        # constructor.
        iv = self.urandom(BLOCK_SIZE)

        return iv + self.__create_cipher(iv).encrypt(data)

    def decrypt(self, data):
        return self.__create_cipher(data[:BLOCK_SIZE]).decrypt(data[BLOCK_SIZE:])

    def __create_cipher(self, iv):
        # The 'BlockAlgo' class is stateful, this factory method is used to
        # re-initialize the block cipher class with each call to encrypt() and
        # decrypt().
        return AES.new(self.key, AES.MODE_CFB, iv)
