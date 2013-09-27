#! /usr/bin/env python
#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import os
import sys


# Expand PYTHONPATH with PyInstaller package to support running without
# installation.
pyi_home = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, pyi_home)


if __name__ == '__main__':
    from PyInstaller.cliutils.makespec import run
    run()
