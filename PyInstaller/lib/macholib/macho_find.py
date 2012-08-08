#!/usr/bin/env python
from __future__ import print_function
from macholib._cmdline import main as _main


def print_file(fp, path):
    print(path, file=fp)

def main():
    _main(print_file)

if __name__ == '__main__':
    try:
        main(print_file)
    except KeyboardInterrupt:
        pass
