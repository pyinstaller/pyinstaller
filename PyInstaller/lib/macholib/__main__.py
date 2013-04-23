from __future__ import print_function, absolute_import
import os, sys

from macholib.util import is_platform_file
from macholib import macho_dump
from macholib import macho_standalone

gCommand = None

def check_file(fp, path, callback):
    if not os.path.exists(path):
        print('%s: %s: No such file or directory' % (gCommand, path), 
                file=sys.stderr)
        return 1

    try:
        is_plat = is_platform_file(path)

    except IOError as msg:
        print('%s: %s: %s' % (gCommand, path, msg), file=sys.stderr)
        return 1

    else:
        if is_plat:
            callback(fp, path)
    return 0

def walk_tree(callback, paths):
    args = sys.argv[1:]
    err = 0

    for base in paths:
        if os.path.isdir(base):
            for root, dirs, files in os.walk(base):
                for fn in files:
                    err |= check_file(
                            sys.stdout, os.path.join(root, fn), callback)
        else:
            err |= check_file(sys.stdout, base, callback)

    return err

def print_usage(fp):
    print("Usage:", file=sys.stderr)
    print("  python -mmacholib dump FILE ...", file=fp)
    print("  python -mmacholib find DIR ...", file=fp)
    print("  python -mmacholib standalone DIR ...", file=fp)

def main():
    global gCommand
    if len(sys.argv) < 3:
        print_usage(sys.stderr)
        sys.exit(1)

    gCommand = sys.argv[1]

    if gCommand == 'dump':
        walk_tree(macho_dump.print_file, sys.argv[2:])

    elif gCommand == 'find':
        walk_tree(lambda fp, path: print(path, file=fp), sys.argv[2:])

    elif gCommand == 'standalone':
        for dn in sys.argv[2:]:
            macho_standalone.standaloneApp(dn)

    else:
        print_usage(sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
