#-----------------------------------------------------------------------------
# Copyright (c) 2013-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Viewer for archives packaged by archive.py
"""

from __future__ import print_function

import argparse
import os
import pprint
import tempfile
import zlib

from PyInstaller.loader import pyimod02_archive
from PyInstaller.archive.readers import CArchiveReader, NotAnArchiveError
from PyInstaller.compat import stdin_input
import PyInstaller.log

stack = []
cleanup = []


def main(name, brief, debug, rec_debug, **unused_options):

    global stack

    if not os.path.isfile(name):
        print(name, "is an invalid file name!")
        return 1

    arch = get_archive(name)
    stack.append((name, arch))
    if debug or brief:
        show_log(arch, rec_debug, brief)
        raise SystemExit(0)
    else:
        show(name, arch)

    while 1:
        try:
            toks = stdin_input('? ').split(None, 1)
        except EOFError:
            # Ctrl-D
            print()  # Clear line.
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
            name, arch = stack[-1]
            show(name, arch)
        elif cmd == 'O':
            if not arg:
                arg = stdin_input('open name? ')
            arg = arg.strip()
            try:
                arch = get_archive(arg)
            except NotAnArchiveError as e:
                print(e)
                continue
            if arch is None:
                print(arg, "not found")
                continue
            stack.append((arg, arch))
            show(arg, arch)
        elif cmd == 'X':
            if not arg:
                arg = stdin_input('extract name? ')
            arg = arg.strip()
            data = get_data(arg, arch)
            if data is None:
                print("Not found")
                continue
            filename = stdin_input('to filename? ')
            if not filename:
                print(repr(data))
            else:
                open(filename, 'wb').write(data)
        elif cmd == 'Q':
            break
        else:
            usage()
    do_cleanup()


def do_cleanup():
    global stack, cleanup
    for (name, arch) in stack:
        arch.lib.close()
    stack = []
    for filename in cleanup:
        try:
            os.remove(filename)
        except Exception as e:
            print("couldn't delete", filename, e.args)
    cleanup = []


def usage():
    print("U: go Up one level")
    print("O <name>: open embedded archive name")
    print("X <name>: extract name")
    print("Q: quit")


def get_archive(name):
    if not stack:
        if name[-4:].lower() == '.pyz':
            return ZlibArchive(name)
        return CArchiveReader(name)
    parent = stack[-1][1]
    try:
        return parent.openEmbedded(name)
    except KeyError:
        return None
    except (ValueError, RuntimeError):
        ndx = parent.toc.find(name)
        dpos, dlen, ulen, flag, typcd, name = parent.toc[ndx]
        x, data = parent.extract(ndx)
        tempfilename = tempfile.mktemp()
        cleanup.append(tempfilename)
        open(tempfilename, 'wb').write(data)
        if typcd == 'z':
            return ZlibArchive(tempfilename)
        else:
            return CArchiveReader(tempfilename)


def get_data(name, arch):
    if isinstance(arch.toc, dict):
        (ispkg, pos, length) = arch.toc.get(name, (0, None, 0))
        if pos is None:
            return None
        with arch.lib:
            arch.lib.seek(arch.start + pos)
            return zlib.decompress(arch.lib.read(length))
    ndx = arch.toc.find(name)
    dpos, dlen, ulen, flag, typcd, name = arch.toc[ndx]
    x, data = arch.extract(ndx)
    return data


def show(name, arch):
    if isinstance(arch.toc, dict):
        print(" Name: (ispkg, pos, len)")
        toc = arch.toc
    else:
        print(" pos, length, uncompressed, iscompressed, type, name")
        toc = arch.toc.data
    pprint.pprint(toc)


def get_content(arch, recursive, brief, output):
    if isinstance(arch.toc, dict):
        toc = arch.toc
        if brief:
            for name, _ in toc.items():
                output.append(name)
        else:
            output.append(toc)
    else:
        toc = arch.toc.data
        for el in toc:
            if brief:
                output.append(el[5])
            else:
                output.append(el)
            if recursive:
                if el[4] in ('z', 'a'):
                    get_content(get_archive(el[5]), recursive, brief, output)
                    stack.pop()


def show_log(arch, recursive, brief):
    output = []
    get_content(arch, recursive, brief, output)
    # first print all TOCs
    for out in output:
        if isinstance(out, dict):
            pprint.pprint(out)
    # then print the other entries
    pprint.pprint([out for out in output if not isinstance(out, dict)])


def get_archive_content(filename):
    """
    Get a list of the (recursive) content of archive `filename`.

    This function is primary meant to be used by runtests.
    """
    archive = get_archive(filename)
    stack.append((filename, archive))
    output = []
    get_content(archive, recursive=True, brief=True, output=output)
    do_cleanup()
    return output


class ZlibArchive(pyimod02_archive.ZlibArchiveReader):

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
            print("Warning: pyz is from a different Python version")
        self.lib.read(4)


def run():
    PyInstaller.log.init()

    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--log',
                        default=False,
                        action='store_true',
                        dest='debug',
                        help='Print an archive log (default: %(default)s)')
    parser.add_argument('-r', '--recursive',
                        default=False,
                        action='store_true',
                        dest='rec_debug',
                        help='Recursively print an archive log (default: %(default)s). '
                        'Can be combined with -r')
    parser.add_argument('-b', '--brief',
                        default=False,
                        action='store_true',
                        dest='brief',
                        help='Print only file name. (default: %(default)s). '
                        'Can be combined with -r')
    PyInstaller.log.__add_options(parser)
    parser.add_argument('name', metavar='pyi_archive',
                        help="pyinstaller archive to show content of")

    args = parser.parse_args()
    PyInstaller.log.__process_options(parser, args)

    try:
        raise SystemExit(main(**vars(args)))
    except KeyboardInterrupt:
        raise SystemExit("Aborted by user request.")

if __name__ == '__main__':
    run()

