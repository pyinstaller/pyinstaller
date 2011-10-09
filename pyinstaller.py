#! /usr/bin/env python
#
# Wrapper around Configure.py / Makespec.py / Build.py
#
# Copyright (C) 2010, Martin Zibricky
# Copyright (C) 2011, Hartmut Goebel
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

import os
import optparse

import PyInstaller.configure
import PyInstaller.makespec
import PyInstaller.build
import PyInstaller.compat
import PyInstaller.log


# Warn when old command line option is used

from PyInstaller import get_version


def run_configure(opts, args):
    PyInstaller.configure.main(**opts.__dict__)


def run_makespec(opts, args):
    # Split pathex by using the path separator
    temppaths = opts.pathex[:]
    opts.pathex = []
    for p in temppaths:
        opts.pathex.extend(p.split(os.pathsep))

    spec_file = PyInstaller.makespec.main(args, **opts.__dict__)
    print 'wrote %s' % spec_file
    return spec_file


def run_build(opts, spec_file):
    PyInstaller.build.main(spec_file, **opts.__dict__)


def __add_options(parser):
    parser.add_option('-v', '--version', default=False, action='store_true',
                      help='show program version')
    parser.add_option('--skip-configure', default=False, action='store_true',
                      help='Skip configure phase.'
                      'Configure phase can be skipped to speed up pyinstaller '
                      'if running multiple times with the same configuration.')


def main():
    parser = optparse.OptionParser(
        usage='python %prog [opts] <scriptname> [ <scriptname> ...] | <specfile>'
        )
    __add_options(parser)
    PyInstaller.configure.__add_options(parser)
    PyInstaller.makespec.__add_options(parser)
    PyInstaller.build.__add_options(parser)
    PyInstaller.log.__add_options(parser)
    PyInstaller.compat.__add_obsolete_options(parser)

    opts, args = parser.parse_args()
    PyInstaller.log.__process_options(parser, opts)

    # Print program version and exit
    if opts.version:
        print get_version()
        raise SystemExit(0)

    if not args:
        parser.error('Requires at least one scriptname file '
                     'or exactly one .spec-file')

    # Skip configure when --skip-configure option present
    if not opts.skip_configure:
        run_configure(opts, args)

    # Skip creating .spec when .spec file is supplied
    if args[0].endswith('.spec'):
        spec_file = args[0]
    else:
        spec_file = run_makespec(opts, args)

    run_build(opts, spec_file)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit("Aborted by user request.")
