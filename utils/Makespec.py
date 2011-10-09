#! /usr/bin/env python
#
# Automatically build spec files containing a description of the project
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

try:
    import PyInstaller
except ImportError:
    # if importing PyInstaller fails, try to load from parent
    # directory to support running without installation
    import imp, os
    if not hasattr(os, 'getuid') or os.getuid() != 0:
        imp.load_module('PyInstaller', *imp.find_module('PyInstaller',
            [os.path.dirname(os.path.dirname(__file__))]))

import PyInstaller.makespec
import PyInstaller.compat
import PyInstaller.log
import optparse

import os

p = optparse.OptionParser(
    usage='python %prog [opts] <scriptname> [<scriptname> ...]'
)
p.add_option('-C', '--configfile',
             default=PyInstaller.DEFAULT_CONFIGFILE,
             dest='configfilename',
             help='Name of configfile (default: %default)')
PyInstaller.makespec.__add_options(p)
PyInstaller.log.__add_options(p)
PyInstaller.compat.__add_obsolete_options(p)

opts, args = p.parse_args()
PyInstaller.log.__process_options(p, opts)

# Split pathex by using the path separator
temppaths = opts.pathex[:]
opts.pathex = []
for p in temppaths:
    opts.pathex.extend(p.split(os.pathsep))

if not args:
    p.error('Requires at least one scriptname file')

try:
    name = PyInstaller.makespec.main(args, **opts.__dict__)
    print 'wrote %s' % name
    print 'now run Build.py to build the executable'
except KeyboardInterrupt:
    raise SystemExit("Aborted by user request.")
