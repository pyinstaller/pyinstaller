#!/usr/bin/env python
#
# Build packages using spec files
#
# Copyright (C) 2005-2011, Giovanni Bajo
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA


import glob
import optparse
import os


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


import PyInstaller.bindepend
from PyInstaller import is_win
import PyInstaller.log


parser = optparse.OptionParser(
        usage='python %prog <executable_or_dynamic_library> '
        '[ <executable_or_dynamic_library> ... ]')
PyInstaller.log.__add_options(parser)

opts, args = parser.parse_args()
PyInstaller.log.__process_options(parser, opts)
if len(args) == 0:
    parser.error('Requires one or more executables or dynamic libraries')

# Suppress all informative messages from the dependency code.
PyInstaller.log.getLogger('PyInstaller.build.bindepend').setLevel(
        PyInstaller.log.WARN)

try:
    for a in args:
        for fn in glob.glob(a):
            imports = PyInstaller.bindepend.getImports(fn)
            if is_win:
                assemblies = PyInstaller.bindepend.getAssemblies(fn)
                imports.update([a.getid() for a in assemblies])
            print fn, imports
except KeyboardInterrupt:
    raise SystemExit("Aborted by user request.")
