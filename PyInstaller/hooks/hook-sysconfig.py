#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# The 'sysconfig' module requires Makefile and pyconfig.h files from
# Python installation. 'sysconfig' parses these files to get some
# information from them.

import sysconfig
import os
import sys

from PyInstaller import compat
from PyInstaller.hooks.hookutils import relpath_to_config_or_make

try:
    get_makefile_filename = sysconfig.get_makefile_filename
except AttributeError:
    # Up to Python 2.7.8, get_makefile_filename was private, see
    # http://bugs.python.org/issue22199
    get_makefile_filename = sysconfig._get_makefile_filename

_CONFIG_H = sysconfig.get_config_h_filename()
_MAKEFILE = get_makefile_filename()

datas = []

# work around a bug when running in a virtual environment: sysconfig
# may name a file which actually does not exist, esp. on "multiarch"
# platforms. In this case, ask distutils.sysconfig
if os.path.exists(_CONFIG_H):
    datas.append((_CONFIG_H, relpath_to_config_or_make(_CONFIG_H)))
else:
    import distutils.sysconfig
    datas.append((distutils.sysconfig.get_config_h_filename(),
                  relpath_to_config_or_make(_CONFIG_H)))

# The Makefile does not exist on all platforms, eg. on Windows
if os.path.exists(_MAKEFILE):
    datas.append((_MAKEFILE, relpath_to_config_or_make(_MAKEFILE)))
