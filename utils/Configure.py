#! /usr/bin/env python
#
# Configure PyInstaller for the current Python installation.
#
# Copyright (C) 2005-2011, Giovanni Bajo
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

try:
    import PyInstaller
except ImportError:
    # if importing PyInstaller fails, try to load from parent
    # directory to support running without installation
    import imp, os
    if not hasattr(os, 'getuid') or os.getuid() != 0:
        imp.load_module('PyInstaller', *imp.find_module('PyInstaller',
            [os.path.dirname(os.path.dirname(__file__))]))

import PyInstaller.configure
import PyInstaller.compat
import PyInstaller.log
import optparse

parser = optparse.OptionParser(usage='%prog [options]')
PyInstaller.configure.__add_options(parser)
PyInstaller.log.__add_options(parser)
PyInstaller.compat.__add_obsolete_options(parser)

opts, args = parser.parse_args()
PyInstaller.log.__process_options(parser, opts)
if args:
    parser.error('Does not expect any arguments')

try:
    PyInstaller.configure.main(**opts.__dict__)
except KeyboardInterrupt:
    raise SystemExit("Aborted by user request.")
