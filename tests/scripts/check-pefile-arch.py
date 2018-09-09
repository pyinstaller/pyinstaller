#!/usr/bin/env python
#
# Copyright (c) 2017-2018, PyInstaller Development Team.
# Author: Hartmut Goebel
#
# Verify if a list of pe-files was the expected arch-bits.
#
# Usage: check-pefile-arch.py (32|64) FILEGLOB ...
#
# Since this script targets to win32 command.com, the FILEGLOBs are processed
# in the script.
#
# Note: This code is using raw file-access instead of module `pefile` to be
# used in the CI-tests prior to installing other packages. It does not use
# `argparse` to reduce the overhead and be quick.

from __future__ import print_function

import glob
import struct
import sys

# A more complete list can be found at
# https://stackoverflow.com/questions/1001404/
IMAGE_FILE_MACHINE_AMD64 = 0x8664
IMAGE_FILE_MACHINE_I386 = 0x14c
IMAGE_FILE_MACHINE_IA64 = 0x200

# Basic structure from https://stackoverflow.com/questions/1345632/
def check_pefile(filename):
    with open(filename, "rb") as fh:
        s = fh.read(2)
        if s != b"MZ":
            return None, "Not an PE file"
        else:
            fh.seek(60)
            s = fh.read(4)
            header_offset = struct.unpack("<L", s)[0]
            fh.seek(header_offset + 4)
            s = fh.read(2)
            machine = struct.unpack("<H", s)[0]

    if machine == IMAGE_FILE_MACHINE_I386:
        return 32, "IA-32 (32-bit x86)"
    elif machine == IMAGE_FILE_MACHINE_IA64:
        return 64, "IA-64 (Itanium)"
    elif machine == IMAGE_FILE_MACHINE_AMD64:
        return 64, "AMD64 (64-bit x86)"
    else:
        return None, "Handled architecture: 0x%x" % machine

def check(filename, expected_bits):
    bits, desc = check_pefile(filename)
    okay = True
    msg = "** okay  "
    if bits != expected_bits:
        msg = "** FAILED"
        okay = False
    print(msg, filename, desc, sep="\t")
    return okay


def main():
    expected_bits = int(sys.argv[1])
    okay = True
    for pat in sys.argv[2:]:
        filenames = glob.glob(pat)
        for filename in filenames:
            okay = check(filename, expected_bits) and okay
    if not okay:
        raise SystemExit("*** FAILED.")
    else:
        print("*** Okay.")

if __name__ == '__main__':
    main()
