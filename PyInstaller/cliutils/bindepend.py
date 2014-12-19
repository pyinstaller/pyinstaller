#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Show dll dependencies of executable files or other dynamic libraries.
"""

from __future__ import print_function

import glob
import optparse


import PyInstaller.bindepend
from PyInstaller import is_win
from PyInstaller.utils import misc
import PyInstaller.log


def run():
    misc.check_not_running_as_root()

    parser = optparse.OptionParser(
            usage='python %prog <executable_or_dynamic_library> '
            '[ <executable_or_dynamic_library> ... ]')
    PyInstaller.log.__add_options(parser)

    opts, args = parser.parse_args()
    PyInstaller.log.__process_options(parser, opts)
    if len(args) == 0:
        parser.error('Requires one or more executables or dynamic libraries')

    # Suppress all informative messages from the dependency code.
    PyInstaller.log.getLogger('PyInstaller.build.bindepend').setLevel(
            PyInstaller.log.WARN)

    try:
        for a in args:
            for fn in glob.glob(a):
                imports = PyInstaller.bindepend.getImports(fn)
                if is_win:
                    assemblies = PyInstaller.bindepend.getAssemblies(fn)
                    imports.update([a.getid() for a in assemblies])
                print(fn, imports)
    except KeyboardInterrupt:
        raise SystemExit("Aborted by user request.")
