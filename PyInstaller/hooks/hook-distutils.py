#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import distutils.sysconfig
import marshal
import os
import sys

from PyInstaller import compat


# distutils module requires Makefile and pyconfig.h files from Python
# installation. 'distutils.sysconfig' parses these files to get some
# information from them.
_CONFIG_H = distutils.sysconfig.get_config_h_filename()
_MAKEFILE = distutils.sysconfig.get_makefile_filename()


# In virtualenv, _CONFIG_H and _MAKEFILE may have same or different
# prefixes, depending on the version of virtualenv.
# Try to find the correct one, which is assumed to be the longest one.
def _find_prefix(filename):
    if not compat.is_virtualenv:
        return sys.prefix
    prefixes = [sys.prefix, compat.venv_real_prefix]
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
    return compat.relpath(os.path.dirname(filename), prefix)

# Data files in PyInstaller hook format.
datas = [
    (_CONFIG_H, _relpath(_CONFIG_H))
]


# The Makefile does not exist on all platforms, eg. on Windows
if os.path.exists(_MAKEFILE):
    datas.append((_MAKEFILE, _relpath(_MAKEFILE)))


def hook(mod):
    """
    Contributed by jkp@kirkconsulting.co.uk
    This hook checks for the distutils hacks present when using the
    virtualenv package.
    """
    # Non-empty  means PyInstaller is running inside virtualenv.
    # Virtualenv overrides real distutils modules.
    if hasattr(distutils, 'distutils_path'):
        mod_path = os.path.join(distutils.distutils_path, '__init__.pyc')
        try:
            parsed_code = marshal.loads(open(mod_path, 'rb').read()[8:])
        except IOError:
            parsed_code = compile(open(mod_path[:-1], 'rU').read(), mod_path, 'exec')
        mod.__init__('distutils', mod_path, parsed_code)
    return mod
