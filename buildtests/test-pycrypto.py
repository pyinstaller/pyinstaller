#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
