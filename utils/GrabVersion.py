#! /usr/bin/env python
# Copyright (C) 2005, Giovanni Bajo
# Based on previous work under copyright (c) 2002 McMillan Enterprises, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA

import sys

try:
    import PyInstaller
except ImportError:
    # if importing PyInstaller fails, try to load from parent
    # directory to support running without installation
    import imp, os
    if not hasattr(os, 'getuid') or os.getuid() != 0:
        imp.load_module('PyInstaller', *imp.find_module('PyInstaller',
            [os.path.dirname(os.path.dirname(__file__))]))

from PyInstaller.utils import versioninfo

if len(sys.argv) < 2:
    print 'Usage: >python GrabVersion.py <exe>'
    print ' where: <exe> is the fullpathname of a Windows executable.'
    print ' The printed output may be saved to a file,  editted and '
    print ' used as the input for a verion resource on any of the '
    print ' executable targets in an Installer config file.'
    print ' Note that only NT / Win2K can set version resources.'
else:
    try:
        vs  = versioninfo.decode(sys.argv[1])
        print vs
    except KeyboardInterrupt:
        raise SystemExit("Aborted by user request.")
