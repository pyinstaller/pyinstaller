#!/usr/bin/env python

from macholib._cmdline import main


def print_file(fp, path):
    print >>fp, path

if __name__ == '__main__':
    try:
        main(print_file)
    except KeyboardInterrupt:
        pass
