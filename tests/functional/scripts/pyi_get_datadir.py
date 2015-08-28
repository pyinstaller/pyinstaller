#-----------------------------------------------------------------------------
# Copyright (c) 2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# This module assists in determining the location of the tests/functional/data
# directory.

# Library imports
# ---------------
import sys
import os.path

# Globals
# -------
# Directory storing test-specific data.
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        '..', 'data')

# Functions
# ---------
# This function returns the location of the
# tests/functional/data directory when run from a test, either built by
# Pyinstaller or simply run from the Python interpreter.
def get_data_dir():
    # Some tests need input files to operate on. There are two cases:
    if getattr(sys, 'frozen', False):
        # This local import only works when frozen.
        from pyi_testmod_gettemp import gettemp
        # 1. Frozen: the tests are run in tmpdir/dist/<testname>/tests; data is in
        #    tmpdir/data. Note that dirname(__file__) gives tmpdir/dist/testname.
        return gettemp('data')
    else:
        # 2. Not frozen:
        return DATA_DIR

