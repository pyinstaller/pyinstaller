#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# The 'distutils' module requires Makefile and pyconfig.h files from Python
# installation. 'distutils.sysconfig' parses these files to get some
# information from them.

import distutils
import os
import sys
import sysconfig

from PyInstaller.compat import base_prefix


_CONFIG_H = sysconfig.get_config_h_filename()
_MAKEFILE = sysconfig.get_makefile_filename()


def _relpath(filename):
    # Relative path in the dist directory.
    return os.path.relpath(os.path.dirname(filename), base_prefix)

# Data files in PyInstaller hook format.
datas = [(_CONFIG_H, _relpath(_CONFIG_H))]


# The Makefile does not exist on all platforms, eg. on Windows
if os.path.exists(_MAKEFILE):
    datas.append((_MAKEFILE, _relpath(_MAKEFILE)))


def hook(mod):
    """
    This hook checks for the distutils hacks present when using the
    virtualenv package.
    """
    # Non-empty  means PyInstaller is running inside virtualenv.
    # Virtualenv overrides real distutils modules.
    if hasattr(distutils, 'distutils_path'):
        mod_path = os.path.join(distutils.distutils_path, '__init__.py')
        mod.retarget(mod_path)
    return mod
