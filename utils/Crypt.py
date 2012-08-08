#!/usr/bin/env python
# Crypt support routines
# Copyright (C) 2005, Giovanni Bajo

try:
    import PyInstaller
except ImportError:
    # if importing PyInstaller fails, try to load from parent
    # directory to support running without installation
    import imp, os
    if not hasattr(os, "getuid") or os.getuid() != 0:
        imp.load_module('PyInstaller', *imp.find_module('PyInstaller',
            [os.path.dirname(os.path.dirname(__file__))]))

import sys

class ArgsError(Exception):
    pass

def gen_random_key(size=32):
    """
    Generate a cryptographically-secure random key. This is done by using
    Python 2.4's os.urandom, or PyCrypto.
    """
    import os
    if hasattr(os, "urandom"): # Python 2.4+
        return os.urandom(size)

    # Try using PyCrypto if available
    try:
        from Crypto.Util.randpool import RandomPool
        from Crypto.Hash import SHA256
        return RandomPool(hash=SHA256).get_bytes(size)

    except ImportError:
        print >>sys.stderr, "WARNING: The generated key will not be cryptographically-secure key. Consider using Python 2.4+ to generate the key, or install PyCrypto."

        # Stupid random generation
        import random
        L = []
        for i in range(size):
            L.append(chr(random.randint(0, 255)))
        return "".join(L)

def cmd_genkey(args):
    import pprint
    if len(args) != 1:
        raise ArgsError, "invalid number of arguments"

    key_file = args[0]
    key = gen_random_key()
    f = open(key_file, "w")
    print >>f, "key = %s" % repr(key)
    return 0

def main():
    global global_opts
    global opts
    import optparse

    cmds = {}
    p = optparse.OptionParser(
        usage="%prog [opts] file",
        description="Generate a plaintext keyfile containing a "
                    "random-generated encryption key. ")
    cmds["genkey"] = p

    for c,p in cmds.items():
        p.prog = p.get_prog_name() + " " + c

    cmdnames = cmds.keys()
    cmdnames.sort()
    p = optparse.OptionParser(
        usage="%prog cmd [opts]\n\n" +
              "Available Commands:\n  " +
              "\n  ".join(cmdnames),
        description="This tool is a helper of crypt-related tasks with PyInstaller."
    )

    p.disable_interspersed_args()
    global_opts,args = p.parse_args()
    if not args:
        p.print_usage()
        return -1

    c = args.pop(0)
    if c not in cmds.keys():
        print "invalid command: %s" % c
        return -1

    p = cmds[c]
    opts, args = p.parse_args(args)
    try:
        return globals()["cmd_" + c](args)
    except ArgsError, e:
        p.error(e)

try:
    raise SystemExit(main())
except KeyboardInterrupt:
    raise SystemExit("Aborted by user request.")
