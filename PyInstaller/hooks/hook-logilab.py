#-----------------------------------------------------------------------------
# Copyright (c) 2014, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
#
# ***************************************************
# hook-logilab.py - PyInstaller hook file for logilab
# ***************************************************
from PyInstaller.compat import is_py2
#
# The following was written about logilab, version 0.32.2, based on the contents
# of logilab.common.__pkginfo__.
#
# In logilab.common.configuration, line 126::
#
#    from six.moves import range, configparser as cp, input
#
# Therefore, the modules must be listed as hidden imports, due to the six
# module's lazy import structure. The range module is a builtin, so we
# don't need to list that. The configparser imports as ConfigParser in
# Python 2.
#
# Pyinstaller for Python 3 can auto-detect six imports, so omit it.
if is_py2:
    hiddenimports = ['ConfigParser']

