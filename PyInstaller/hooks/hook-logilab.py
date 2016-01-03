#-----------------------------------------------------------------------------
# Copyright (c) 2014-2016, PyInstaller Development Team.
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
# The following was written about logilab, version 1.1.0, based on executing
# ``pip show logilab-common``.
#
# In logilab.common, line 33::
#
#    __version__ = pkg_resources.get_distribution('logilab-common').version
#
# Therefore, we need metadata for logilab.
from PyInstaller.utils.hooks import copy_metadata

datas = copy_metadata('logilab-common')
