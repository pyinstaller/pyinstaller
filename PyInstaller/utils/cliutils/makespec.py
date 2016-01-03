#-----------------------------------------------------------------------------
# Copyright (c) 2013-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Automatically build spec files containing a description of the project
"""

import argparse
import os

import PyInstaller.building.makespec
import PyInstaller.compat
import PyInstaller.log


def run():
    PyInstaller.log.init()

    p = argparse.ArgumentParser()
    PyInstaller.building.makespec.__add_options(p)
    PyInstaller.log.__add_options(p)
    PyInstaller.compat.__add_obsolete_options(p)
    p.add_argument('scriptname', nargs='+')

    args = p.parse_args()
    PyInstaller.log.__process_options(p, args)

    # Split pathex by using the path separator
    temppaths = args.pathex[:]
    args.pathex = []
    for p in temppaths:
        args.pathex.extend(p.split(os.pathsep))

    try:
        name = PyInstaller.building.makespec.main(args.scriptname, **vars(args))
        print('wrote %s' % name)
        print('now run pyinstaller.py to build the executable')
    except KeyboardInterrupt:
        raise SystemExit("Aborted by user request.")

if __name__ == '__main__':
    run()
