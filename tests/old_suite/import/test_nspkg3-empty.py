#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Test inclusion of a namespace-only packages in an zipped egg using
# pkgutil.extend_path.
# This package only defines namespace, nothing is contained there.

import sys
if not getattr(sys, 'frozen', None):
    import os
    sys.path.append(os.path.join(
        os.path.dirname(__file__), 'nspkg3-pkg', 'nspkg3_empty.egg'))

import nspkg3
print (nspkg3)
