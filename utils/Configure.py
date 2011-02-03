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

import PyInstaller.configure

if __name__ == '__main__':
    from PyInstaller.lib.pyi_optparse import OptionParser
    parser = OptionParser(usage="%prog [options]")
    parser.add_option('--target-platform', default=None,
                      help='Target platform, required for cross-bundling '
                           '(default: current platform).')
    parser.add_option('--upx-dir', default=None,
                      help='Directory containing UPX.')
    parser.add_option('--executable', default=None,
                      help='Python executable to use. Required for '
                           'cross-bundling.')
    parser.add_option('-C', '--configfile',
                      default=PyInstaller.configure.DEFAULT_CONFIGFILE,
                      help='Name of generated configfile (default: %default)')

    opts, args = parser.parse_args()
    if args:
        parser.error('Does not expect any arguments')

    # :HACK: monkey-patch global variable in module
    PyInstaller.configure.opts = opts
    PyInstaller.configure.args = args
    PyInstaller.configure.main(opts.configfile)
