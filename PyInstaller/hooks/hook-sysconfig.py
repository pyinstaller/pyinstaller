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
from PyInstaller.utils.hooks.hookutils import relpath_to_config_or_make

_CONFIG_H = sysconfig.get_config_h_filename()
_MAKEFILE = sysconfig.get_makefile_filename()


datas = [(_CONFIG_H, relpath_to_config_or_make(_CONFIG_H))]

# The Makefile does not exist on all platforms, eg. on Windows
if os.path.exists(_MAKEFILE):
    datas.append((_MAKEFILE, relpath_to_config_or_make(_MAKEFILE)))