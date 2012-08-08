#!/usr/bin/env python

from __future__ import print_function

import os
import sys

from macholib._cmdline import main as _main
from macholib.MachO import MachO
from macholib.mach_o import *

ARCH_MAP={
    ('<', '64-bit'): 'x86_64',
    ('<', '32-bit'): 'i386',
    ('>', '64-bit'): 'pp64',
    ('>', '32-bit'): 'ppc',
}

def print_file(fp, path):
    print(path, file=fp)
    m = MachO(path)
    for header in m.headers:
        seen = set()
        if header.MH_MAGIC == MH_MAGIC_64:
            sz = '64-bit'
        else:
            sz = '32-bit'

        print('    [%s endian=%r size=%r arch=%r]' % (header.__class__.__name__, 
                header.endian, sz, ARCH_MAP[(header.endian, sz)]), file=fp)
        for idx, name, other in header.walkRelocatables():
            if other not in seen:
                seen.add(other)
                print('\t' + other, file=fp)

def main():
    _main(print_file)

if __name__ == '__main__':
    try:
        sys.exit(main(print_file))
    except KeyboardInterrupt:
        pass
