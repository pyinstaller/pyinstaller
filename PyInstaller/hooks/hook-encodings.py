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
from distutils import sysconfig
hiddenimports = []
libpath = sysconfig.get_python_lib(plat_specific=0, standard_lib=1)
for f in glob.glob(os.path.join(libpath, "encodings", "*.py")):
    f = os.path.basename(f)
    f = os.path.splitext(f)[0]
    if f != "__init__":
        hiddenimports.append(f)
