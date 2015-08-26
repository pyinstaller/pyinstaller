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

# Global variables
# ----------------
_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
# Return the subdirectory data/ of the current file's directory.
DATA_DIR = os.path.join(_FILE_DIR, 'data')

# Functions
# ---------
# This function returns the location of the
# tests/functional/data directory when run from a test, either built by
# Pyinstaller or simply run from the Python interpreter.
def get_data_dir():
    # Some tests need input files to operate on. There are two cases:
    if getattr(sys, 'frozen', False):
        # 1. Frozen: the tests are run in tmpdir/dist/<testname>/tests; data is in
        #    tmpdir/data. Note that dirname(__file__) gives tmpdir/dist/testname.
        print(_FILE_DIR)
        return os.path.join(_FILE_DIR, '..', '..', '..', '..', 'data')
    else:
        # 2. Not frozen:
        return DATA_DIR

