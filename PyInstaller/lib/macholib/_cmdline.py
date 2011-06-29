"""
Internal helpers for basic commandline tools
"""
import os
import sys

from macholib.util import is_platform_file

def check_file(fp, path, callback):
    if not os.path.exists(path):
        print >>sys.stderr, '%s: %s: No such file or directory' % (sys.argv[0], path)
        return 1

    try:
        is_plat = is_platform_file(path)

    except IOError, msg:
        print >>sys.stderr, '%s: %s: %s' % (sys.argv[0], path, msg)
        return 1

    else:
        if is_plat:
            callback(fp, path)
    return 0

def main(callback):
    args = sys.argv[1:]
    name = os.path.basename(sys.argv[0])
    err = 0

    if not args:
        print >>sys.stderr, "Usage: %s filename..."%(name,)
        return 1

    for base in args:
        if os.path.isdir(base):
            for root, dirs, files in os.walk(base):
                for fn in files:
                    err |= check_file(sys.stdout, os.path.join(root, fn), callback)
        else:
            err |= check_file(sys.stdout, base, callback)

    return err
