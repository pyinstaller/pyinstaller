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
Build packages using spec files
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
