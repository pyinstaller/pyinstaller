#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Test inclusion of PEP 420 namespace packages.

import sys
if not getattr(sys, 'frozen', None):
    # When running un-frozen, add extend the path like `pathex` does
    # in the .spec-file.
    import os
    import glob
    sys.path.extend(glob.glob(
        os.path.join(os.path.dirname(__file__), 'nspkg-pep420', 'path*')))

import package.sub1
import package.sub2
import package.subpackage.sub
import package.nspkg.mod
