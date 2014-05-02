#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


#encodings',
attrs = [('search_function',0)]

import os, sys, glob
import encodings

libpath = os.path.dirname(os.path.dirname(os.path.realpath(encodings.__file__)))

hiddenimports = []
for f in glob.glob(os.path.join(libpath, "encodings", "*.py")):
    f = os.path.basename(f)
    f = os.path.splitext(f)[0]
    if f != "__init__":
        hiddenimports.append('encodings.%s' % f)
