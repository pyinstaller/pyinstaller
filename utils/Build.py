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


import PyInstaller.build
import PyInstaller.compat
import PyInstaller.log


parser = optparse.OptionParser(usage='%prog [options] specfile')
PyInstaller.build.__add_options(parser)
PyInstaller.log.__add_options(parser)
PyInstaller.compat.__add_obsolete_options(parser)


opts, args = parser.parse_args()
PyInstaller.log.__process_options(parser, opts)
if len(args) != 1:
    parser.error('Requires exactly one .spec-file')

try:
    PyInstaller.build.main(args[0], **opts.__dict__)
except KeyboardInterrupt:
    raise SystemExit("Aborted by user request.")
