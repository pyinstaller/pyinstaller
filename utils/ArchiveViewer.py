#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Viewer for archives packaged by archive.py
"""


import optparse
import os
import pprint
import tempfile
import zlib


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
import PyInstaller.log


stack = []
cleanup = []
name = None
debug = False
rec_debug = False
brief = False


def main(opts, args):
    global stack
    global debug
    global rec_debug
    global name
    global brief
    name = args[0]
    debug = opts.log
    rec_debug = opts.rec
    brief = opts.brief
    if not os.path.isfile(name):
        print "%s is an invalid file name!" % name
        return 1

    arch = get_archive(name)
    stack.append((name, arch))
    if debug or brief:
        show_log(name, arch)
        raise SystemExit(0)
    else:
        show(name, arch)

    while 1:
        try:
            toks = raw_input('? ').split(None, 1)
        except EOFError:
            # Ctrl-D
            print  # Clear line.
            break
        if not toks:
            usage()
            continue
        if len(toks) == 1:
            cmd = toks[0]
            arg = ''
        else:
            cmd, arg = toks
        cmd = cmd.upper()
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
            arg = arg.strip()
            arch = get_archive(arg)
            if arch is None:
                print arg, "not found"
                continue
            stack.append((arg, arch))
            show(arg, arch)
        elif cmd == 'X':
            if not arg:
                arg = raw_input('extract name? ')
            arg = arg.strip()
            data = get_data(arg, arch)
            if data is None:
                print "Not found"
                continue
            fnm = raw_input('to filename? ')
            if not fnm:
                print repr(data)
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
        dpos, dlen, ulen, flag, typcd, nm = parent.toc[ndx]
        x, data = parent.extract(ndx)
        tfnm = tempfile.mktemp()
        cleanup.append(tfnm)
        open(tfnm, 'wb').write(data)
        if typcd == 'z':
            return ZlibArchive(tfnm)
        else:
            return pyi_carchive.CArchive(tfnm)


def get_data(nm, arch):
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


def show_log(nm, arch, output=[]):
    if type(arch.toc) == type({}):
        toc = arch.toc
        if brief:
            for name, _ in toc.items():
                output.append(name)
        else:
            pprint.pprint(toc)
    else:
        toc = arch.toc.data
        for el in toc:
            if brief:
                output.append(el[5])
            else:
                output.append(el)
            if rec_debug:
                if el[4] in ('z', 'a'):
                    show_log(el[5], get_archive(el[5]), output)
                    stack.pop()
        pprint.pprint(output)


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
parser.add_option('-l', '--log',
                  default=False,
                  action='store_true',
                  dest='log',
                  help='Print an archive log (default: %default)')
parser.add_option('-r', '--recursive',
                  default=False,
                  action='store_true',
                  dest='rec',
                  help='Recusively print an archive log (default: %default). '
                  'Can be combined with -r')
parser.add_option('-b', '--brief',
                  default=False,
                  action='store_true',
                  dest='brief',
                  help='Print only file name. (default: %default). '
                  'Can be combined with -r')
PyInstaller.log.__add_options(parser)

opts, args = parser.parse_args()
PyInstaller.log.__process_options(parser, opts)
if len(args) != 1:
    parser.error('Requires exactly one pyinstaller archive')

try:
    raise SystemExit(main(opts, args))
except KeyboardInterrupt:
    raise SystemExit("Aborted by user request.")
