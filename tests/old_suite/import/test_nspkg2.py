#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Test inclusion of namespace packages implemented as nspkg.pth-files

# Since this .pth-file does not reside on a site-dir, we need to add
# it manually
import sys
if not getattr(sys, 'frozen', None):
    import site
    import os
    site.addsitedir(os.path.join(os.path.dirname(__file__), 'nspkg2-pkg'))

import nspkg2.aaa
import nspkg2.bbb.zzz
import nspkg2.ccc
