#!/usr/bin/env python
#
# Crypt support routines
#
# Copyright (C) 2005, Giovanni Bajo
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA


import os


class ArgsError(Exception):
    pass


def gen_random_key(size=32):
    """
    Generate a cryptographically-secure random key. This is done by using
    Python 2.4's os.urandom.
    """
    return os.urandom(size)


def cmd_genkey(args):
    if len(args) != 1:
        raise ArgsError('Invalid number of arguments.')

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

    for c, p in cmds.items():
        p.prog = p.get_prog_name() + " " + c

    cmdnames = cmds.keys()
    cmdnames.sort()
    p = optparse.OptionParser(
        usage="%prog cmd [opts]\n\n" +
              "Available Commands:\n  " +
              "\n  ".join(cmdnames),
        description='This tool is a helper of crypt-related tasks '
        'with PyInstaller.'
    )

    p.disable_interspersed_args()
    global_opts, args = p.parse_args()
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
