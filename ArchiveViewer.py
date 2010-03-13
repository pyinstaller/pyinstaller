#! /usr/bin/env python
# Viewer for archives packaged by archive.py
# Copyright (C) 2005, Giovanni Bajo
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA
import archive
import carchive
import sys, string, tempfile, os
try:
    import zlib
except ImportError:
    zlib = archive.DummyZlib()
import pprint

stack = []
cleanup = []

def main():
    global stack
    name = sys.argv[1]
    arch = getArchive(name)
    stack.append((name, arch))
    show(name, arch)

    while 1:
        try:
            toks = string.split(raw_input('? '), None, 1)
        except EOFError:
            # Ctrl-D
            print # clear line
            break
        if not toks:
            usage()
            continue
        if len(toks) == 1:
            cmd = toks[0]
            arg = ''
        else:
            cmd, arg = toks
        cmd = string.upper(cmd)
        if cmd == 'U':
            if len(stack) > 1:
                arch = stack[-1][1]
                arch.lib.close()
                del stack[-1]
            nm, arch = stack[-1]
            show(nm, arch)
        elif cmd == 'O':
            if not arg:
                arg = raw_input('open name? ')
            arg = string.strip(arg)
            arch = getArchive(arg)
            if arch is None:
                print arg, "not found"
                continue
            stack.append((arg, arch))
            show(arg, arch)
        elif cmd == 'X':
            if not arg:
                arg = raw_input('extract name? ')
            arg = string.strip(arg)
            data = getData(arg, arch)
            if data is None:
                print "Not found"
                continue
            fnm = raw_input('to filename? ')
            if not fnm:
                print `data`
            else:
                open(fnm, 'wb').write(data)
        elif cmd == 'Q':
            break
        else:
            usage()
    for (nm, arch) in stack:
        arch.lib.close()
    stack = []
    for fnm in cleanup:
        try:
            os.remove(fnm)
        except Exception, e:
            print "couldn't delete", fnm, e.args
def usage():
    print "U: go Up one level"
    print "O <nm>: open embedded archive nm"
    print "X <nm>: extract nm"
    print "Q: quit"
def getArchive(nm):
    if not stack:
        if string.lower(nm[-4:]) == '.pyz':
            return ZlibArchive(nm)
        return carchive.CArchive(nm)
    parent = stack[-1][1]
    try:
        return parent.openEmbedded(nm)
    except KeyError, e:
        return None
    except (ValueError, RuntimeError):
        ndx = parent.toc.find(nm)
        dpos, dlen, ulen, flag, typcd, nm = parent.toc[ndx]
        x, data = parent.extract(ndx)
        tfnm = tempfile.mktemp()
        cleanup.append(tfnm)
        open(tfnm, 'wb').write(data)
        if typcd == 'z':
            return ZlibArchive(tfnm)
        else:
            return carchive.CArchive(tfnm)

def getData(nm, arch):
    if type(arch.toc) is type({}):
        (ispkg, pos, lngth) = arch.toc.get(nm, (0, None, 0))
        if pos is None:
            return None
        arch.lib.seek(arch.start + pos)
        return zlib.decompress(arch.lib.read(lngth))
    ndx = arch.toc.find(nm)
    dpos, dlen, ulen, flag, typcd, nm = arch.toc[ndx]
    x, data = arch.extract(ndx)
    return data

def show(nm, arch):
    if type(arch.toc) == type({}):
        print " Name: (ispkg, pos, len)"
        toc = arch.toc
    else:
        print " pos, length, uncompressed, iscompressed, type, name"
        toc = arch.toc.data
    pprint.pprint(toc)

class ZlibArchive(archive.ZlibArchive):
    def checkmagic(self):
        """ Overridable.
            Check to see if the file object self.lib actually has a file
            we understand.
        """
        self.lib.seek(self.start)       #default - magic is at start of file
        if self.lib.read(len(self.MAGIC)) != self.MAGIC:
            raise RuntimeError, "%s is not a valid %s archive file" \
              % (self.path, self.__class__.__name__)
        if self.lib.read(len(self.pymagic)) != self.pymagic:
            print "Warning: pyz is from a different Python version"
        self.lib.read(4)

if __name__ == '__main__':
    main()
