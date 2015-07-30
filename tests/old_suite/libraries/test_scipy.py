#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# General SciPy import.
from scipy import *

# Test import hooks for the following modules.
import scipy.io.matlab
import scipy.sparse.csgraph

# Some other "problematic" scipy submodules.
import scipy.lib
import scipy.linalg
import scipy.signal
