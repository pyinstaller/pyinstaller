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


_CONFIG_H = sysconfig.get_config_h_filename()
_MAKEFILE = sysconfig.get_makefile_filename()

# In virtualenv, _CONFIG_H and _MAKEFILE may have same or different
# prefixes, depending on the version of virtualenv.
# Try to find the correct one, which is assumed to be the longest one.
def _find_prefix(filename):
    if not compat.is_venv:
        return sys.prefix
    prefixes = [os.path.abspath(sys.prefix), compat.base_prefix]
    possible_prefixes = []
    for prefix in prefixes:
        common = os.path.commonprefix([prefix, filename])
        if common == prefix:
            possible_prefixes.append(prefix)
    possible_prefixes.sort(key=lambda p: len(p), reverse=True)
    return possible_prefixes[0]

def _relpath(filename):
    # Relative path in the dist directory.
    prefix = _find_prefix(filename)
    return os.path.relpath(os.path.dirname(filename), prefix)


datas = [(_CONFIG_H, _relpath(_CONFIG_H))]

# The Makefile does not exist on all platforms, eg. on Windows
if os.path.exists(_MAKEFILE):
    datas.append((_MAKEFILE, _relpath(_MAKEFILE)))
