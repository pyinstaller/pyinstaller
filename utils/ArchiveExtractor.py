#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Extractor for archives packaged by archive.py"""

# Copyright (C) 2013, Dhiru Kholia (dhiru at openwall.com)
#
# Thanks Ned Batchelder, Andreas Stührk for ideas and Przemysław Węgrzyn
# for inspiration.
#
# Copyright (C) 2005-2011, Giovanni Bajo
# Based on previous work under copyright (c) 2002 McMillan Enterprises, Inc.
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


import optparse
import os
import tempfile
import zlib
import struct
import sys


try:
    import PyInstaller
except ImportError:
    # if importing PyInstaller fails, try to load from parent
    # directory to support running without installation.
    import imp
    # Prevent running as superuser (root).
    if not hasattr(os, "getuid") or os.getuid() != 0:
        imp.load_module('PyInstaller', *imp.find_module('PyInstaller',
            [os.path.dirname(os.path.dirname(os.path.abspath(__file__)))]))

from PyInstaller.loader import pyi_archive, pyi_carchive

stack = []
cleanup = []
pyvers = None
destdir = None


def main(opts, args):
    global stack
    global pyvers
    global destdir
    name = args[0]
    if not os.path.isfile(name):
        print "%s is an invalid file name!" % name
        return 1

    with open(name, 'rb') as exe_file:
        exe_data = exe_file.read()

    try:
        pyvers = str(COOKIE(exe_data[-COOKIE.size:]).pyvers)
    except AssertionError:
        print >> sys.stderr, "Error parsing archive, is this a valid PyInstaller generated app?"
        return

    arch = get_archive(name)
    stack.append((name, arch))
    destdir = opts.destdir
    extract_archive(name, arch)

    print "\nFile(s) were extracted to %s directory." % destdir


def get_archive(nm):
    if not stack:
        if nm[-4:].lower() == '.pyz':
            return ZlibArchive(nm)
        return pyi_carchive.CArchive(nm)
    parent = stack[-1][1]
    try:
        return parent.openEmbedded(nm)
    except KeyError:
        return None
    except (ValueError, RuntimeError):
        ndx = parent.toc.find(nm)
        _, dlen, _, _, typcd, nm = parent.toc[ndx]
        _, data = parent.extract(ndx)
        tfnm = tempfile.mktemp()
        cleanup.append(tfnm)
        open(tfnm, 'wb').write(data)
        if typcd == 'z':
            return ZlibArchive(tfnm)
        else:
            return pyi_carchive.CArchive(tfnm)


class COOKIE():
    """COOKIE magic (see bootloader/common/pyi_archive.h)"""
    MAGIC = 'MEI\014\013\012\013\016'

    def __init__(self, data):
        # check magic
        assert data[0:len(COOKIE.MAGIC)] == COOKIE.MAGIC
        data = data[len(COOKIE.MAGIC):COOKIE.isize]
        (self.len, self.TOC, self.TOClen, self.pyvers) = struct.unpack('!4i', data)

    isize = struct.calcsize('!4i') + len(MAGIC)
    size = isize + 64  # for "char pylibname[64]" field


def get_data(nm, arch):
    if isinstance(arch.toc, dict):
        (ispkg, pos, lngth) = arch.toc.get(nm, (0, None, 0))
        if pos is None:
            return None
        arch.lib.seek(arch.start + pos)
        return zlib.decompress(arch.lib.read(lngth))
    ndx = arch.toc.find(nm)
    dpos, dlen, ulen, flag, typcd, nm = arch.toc[ndx]
    x, data = arch.extract(ndx)
    return data


def extract_archive(nm, arch, output=[]):
    if isinstance(arch.toc, dict):
        toc = arch.toc
        for item in toc.items():
            name = item[0]
            data = get_data(name, arch)
            # the following is not fool-proof!
            if "27" in pyvers:
                data = "\x03\xf3\x0d\x0a" + "\x00\x00\x00\x00" + data
            elif "26" in pyvers:
                data = "\xd1\xf2\x0d\x0a" + "\x00\x00\x00\x00" + data
            elif "25" in pyvers:
                data = "\xb3\xf2\x0d\x0a" + "\x00\x00\x00\x00" + data
            path = os.path.join(destdir, name.replace('.', '/'))
            # is this always right?
            path += ".pyc"
            basepath = os.path.dirname(path)
            try:
                os.makedirs(basepath)
            except:
                pass

            print "Extracting bytecode to %s" % path
            with open(path, "wb") as f:
                f.write(data)

    else:
        toc = arch.toc.data
        for el in toc:
            if el[4] in ('s'):
                name = el[5]
                data = get_data(name, arch)
                name += ".py"
                path = os.path.join(destdir, name)
                print "Extracting source to %s" % path
                with open(path, "wb") as f:
                    f.write(data)
            else:
                output.append(el)
            if el[4] in ('z', 'a'):
                extract_archive(el[5], get_archive(el[5]), output)
                stack.pop()


class ZlibArchive(pyi_archive.ZlibArchive):

    def checkmagic(self):
        """ Overridable.
            Check to see if the file object self.lib actually has a file
            we understand.
        """
        self.lib.seek(self.start)  # default - magic is at start of file.
        if self.lib.read(len(self.MAGIC)) != self.MAGIC:
            raise RuntimeError("%s is not a valid %s archive file"
                               % (self.path, self.__class__.__name__))
        if self.lib.read(len(self.pymagic)) != self.pymagic:
            print "Warning: pyz is from a different Python version"
        self.lib.read(4)


parser = optparse.OptionParser('%prog [options] pyi_archive')
parser.add_option('-e', '--extract',
                  default="output",
                  action="store_true",
                  dest='destdir',
                  help='Extract files  to specified directory (default: output). ')


opts, args = parser.parse_args()

if len(args) != 1:
    parser.error('Requires exactly one pyinstaller archive')

try:
    raise SystemExit(main(opts, args))
except KeyboardInterrupt:
    raise SystemExit("Aborted by user request.")
