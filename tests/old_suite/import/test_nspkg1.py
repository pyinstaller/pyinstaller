#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Test inclusion of namespace packages implemented using
# pkg_resources.declare_namespace

import sys
if not getattr(sys, 'frozen', None):
    import os
    import glob
    sys.path.extend(glob.glob(
        os.path.join(os.path.dirname(__file__), 'nspkg1-pkg', 'nspkg1_*.egg')))

import nspkg1.aaa
import nspkg1.bbb.zzz
import nspkg1.ccc
