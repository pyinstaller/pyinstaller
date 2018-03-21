#-----------------------------------------------------------------------------
# Copyright (c) 2013-2018, PyInstaller Development Team.
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
import argparse


import PyInstaller.depend.bindepend
from PyInstaller import is_win
import PyInstaller.log


def run():
    parser = argparse.ArgumentParser()
    PyInstaller.log.__add_options(parser)
    parser.add_argument('filenames', nargs='+',
                        metavar='executable-or-dynamic-library',
                        help=("executables or dynamic libraries for which "
                              "the dependencies should be shown"))

    args = parser.parse_args()
    PyInstaller.log.__process_options(parser, args)

    # Suppress all informative messages from the dependency code.
    PyInstaller.log.getLogger('PyInstaller.build.bindepend').setLevel(
            PyInstaller.log.WARN)

    try:
        for a in args.filenames:
            for fn in glob.glob(a):
                imports = PyInstaller.depend.bindepend.getImports(fn)
                if is_win:
                    assemblies = PyInstaller.depend.bindepend.getAssemblies(fn)
                    imports.update([a.getid() for a in assemblies])
                print(fn, imports)
    except KeyboardInterrupt:
        raise SystemExit("Aborted by user request.")

if __name__ == '__main__':
    run()
