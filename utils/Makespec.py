#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Automatically build spec files containing a description of the project
"""


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


import PyInstaller.makespec
import PyInstaller.compat
import PyInstaller.log


p = optparse.OptionParser(
    usage='python %prog [opts] <scriptname> [<scriptname> ...]'
)
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
