#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Test inclusion of namespace packages implemented using
# pkgutil.extend_path

import sys
if not getattr(sys, 'frozen', None):
    import os
    import glob
    sys.path.extend(glob.glob(
        os.path.join(os.path.dirname(__file__), 'nspkg3-pkg', 'nspkg3_*.egg')))

import nspkg3.aaa
try:
    # pkgutil ignores items of sys.path that are not strings referring
    # to existing directories. So this zipped egg *must* be ignored.
    import nspkg3.bbb.zzz
except ImportError:
    pass
else:
    raise SystemExit("nspkg3.bbb.zzz found but should no")
try:
    import nspkg3.a
except ImportError:
    pass
else:
    raise SystemExit("nspkg3.a found but should no")
import nspkg3.ccc
