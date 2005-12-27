# Copyright (C) 2005, Giovanni Bajo
# Based on previous work under copyright (c) 2001, 2002 McMillan Enterprises, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA

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
