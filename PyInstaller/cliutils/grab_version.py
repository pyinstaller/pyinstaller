#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import os
import sys


try:
    import PyInstaller
except ImportError:
    # if importing PyInstaller fails, try to load from parent
    # directory to support running without installation.
    import imp
    # Prevent running as superuser (root).
    if not hasattr(os, "getuid") or os.getuid() != 0:
        imp.load_module('PyInstaller', *imp.find_module('PyInstaller',
            [os.path.dirname(os.path.dirname(os.path.abspath(__file__)))]))


import PyInstaller.utils.versioninfo

if len(sys.argv) < 2:
    print 'Usage: >python GrabVersion.py <exe>'
    print ' where: <exe> is the fullpathname of a Windows executable.'
    print ' The printed output may be saved to a file,  editted and '
    print ' used as the input for a verion resource on any of the '
    print ' executable targets in an Installer config file.'
    print ' Note that only NT / Win2K can set version resources.'
else:
    try:
        vs = PyInstaller.utils.versioninfo.decode(sys.argv[1])
        print vs
    except KeyboardInterrupt:
        raise SystemExit("Aborted by user request.")
