#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import binascii

from Crypto.Cipher import AES

BLOCK_SIZE = 16


def main():
    print "AES null encryption, block size", BLOCK_SIZE
    # Just for testing functionality after all
    print "HEX", binascii.hexlify(AES.new("\0" * 
                                          BLOCK_SIZE).encrypt("\0" * 
                                                              BLOCK_SIZE))


if __name__ == "__main__":
    main()
