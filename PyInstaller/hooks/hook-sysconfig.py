#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import sysconfig
import os
import sys

from PyInstaller import compat

try:
    get_makefile_filename = sysconfig.get_makefile_filename
except AttributeError:
    # In Python 2.7, get_makefile_filename was private
    get_makefile_filename = sysconfig._get_makefile_filename


def _relpath(filename):
    # Relative path in the dist directory.
    return compat.relpath(os.path.dirname(filename), sys.prefix)

# The 'sysconfig' module requires Makefile and pyconfig.h files from
# Python installation. 'sysconfig' parses these files to get some
# information from them.
_CONFIG_H = sysconfig.get_config_h_filename()
_MAKEFILE = get_makefile_filename()

datas = []

# work around a bug when running in a virtual environment: sysconfig
# may name a file which actually does not exist, esp. on "multiarch"
# platforms. In this case, ask distutils.sysconfig
if os.path.exists(_CONFIG_H):
    datas.append((_CONFIG_H, _relpath(_CONFIG_H)))
else:
    import distutils.sysconfig
    datas.append((distutils.sysconfig.get_config_h_filename(),
                  _relpath(_CONFIG_H)))

# The Makefile does not exist on all platforms, eg. on Windows
if os.path.exists(_MAKEFILE):
    datas.append((_MAKEFILE, _relpath(_MAKEFILE)))
