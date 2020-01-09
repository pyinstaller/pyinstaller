#-----------------------------------------------------------------------------
# Copyright (c) 2014-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
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
