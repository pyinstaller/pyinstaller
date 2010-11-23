#! /usr/bin/env python
#
# Wrapper around Configure.py / Makespec.py / Build.py
#
# Copyright (C) 2010, Martin Zibricky
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
import sys

import Configure
import Makespec
import Build

HOME = os.path.dirname(sys.argv[0])


def run_configure(opts, args):
    Configure.opts = opts
    Configure.args = args
    Configure.main(opts.configfile)


def run_makespec(opts, args):
    # Split pathex by using the path separator
    temppaths = opts.pathex[:]
    opts.pathex = []
    for p in temppaths:
        opts.pathex.extend(p.split(os.pathsep))

    spec_file = Makespec.main(args, **opts.__dict__)
    print "wrote %s" % spec_file
    return spec_file


def run_build(opts, args, spec_file):
    Build.opts = opts
    Build.args = args
    Build.main(spec_file, configfilename=opts.configfile)


def main(parser):
    opts, args = parser.parse_args()
    if not args:
        parser.error('Requires at least one scriptname file or exactly one .spec-file')

    # Skip configuring when using the same python as specified in config.dat
    try:
        config = Build._load_data(opts.configfile)
        if config['pythonVersion'] == sys.version:
            print 'I: skip Configure.py, use existing config', opts.configfile
        else:
            run_configure(opts, args)
    except IOError, SyntaxError:
        run_configure(opts, args)

    # Skip creating .spec when .spec file is supplied 
    if args[0].endswith('.spec'):
        spec_file = args[0]
    else:
        spec_file = run_makespec(opts, args)

    run_build(opts, args, spec_file)


if __name__ == '__main__':
    from pyi_optparse import OptionParser

    parser = OptionParser(
        usage="python %prog [opts] <scriptname> [ <scriptname> ...] | <specfile>"
    )

    # Configure.py options
    g = parser.add_option_group('Python environment')
    g.add_option('--target-platform', default=None,
            help='Target platform, required for cross-bundling '
                 '(default: current platform).')
    g.add_option('--upx-dir', default=None,
            help='Directory containing UPX.')
    g.add_option('--executable', default=None,
            help='Python executable to use. Required for '
                 'cross-bundling.')
    g.add_option('-C', '--configfile',
            default=os.path.join(HOME, 'config.dat'),
            help='Name of generated configfile (default: %default)')

    # Makespec.py options
    g = parser.add_option_group('What to generate')
    g.add_option("-F", "--onefile", dest="freeze",
            action="store_true", default=False,
            help="create a single file deployment")
    g.add_option("-D", "--onedir", dest="freeze", action="store_false",
            help="create a single directory deployment (default)")
    g.add_option("-o", "--out", type="string", default=None,
            dest="workdir", metavar="DIR",
            help="generate the spec file in the specified directory "
                 "(default: current directory")
    g.add_option("-n", "--name", type="string", default=None,
            metavar="NAME",
            help="name to assign to the project "
                 "(default: first script's basename)")

    g = parser.add_option_group('What to bundle, where to search')
    g.add_option("-p", "--paths", type="string", default=[], dest="pathex",
            metavar="DIR", action="append",
            help="set base path for import (like using PYTHONPATH). "
                 "Multiple directories are allowed, separating them "
                 "with %s, or using this option multiple times"
                 % repr(os.pathsep))
    g.add_option("-K", "--tk", default=False, action="store_true",
            help="include TCL/TK in the deployment")
    g.add_option("-a", "--ascii", action="store_true", default=False,
            help="do NOT include unicode encodings "
                 "(default: included if available)")

    g = parser.add_option_group('How to generate')
    g.add_option("-d", "--debug", action="store_true", default=False,
            help="use the debug (verbose) build of the executable")
    g.add_option("-s", "--strip", action="store_true", default=False,
            help="strip the exe and shared libs "
                 "(don't try this on Windows)")
    g.add_option("-X", "--upx", action="store_true", default=True,
            help="use UPX if available (works differently between "
                 "Windows and *nix)")
    #p.add_option("-Y", "--crypt", type="string", default=None, metavar="FILE",
    #       help="encrypt pyc/pyo files")

    g = parser.add_option_group('Windows specific options')
    g.add_option("-c", "--console", "--nowindowed", dest="console",
            action="store_true",
            help="use a console subsystem executable (Windows only) "
                 "(default)")
    g.add_option("-w", "--windowed", "--noconsole", dest="console",
            action="store_false", default=True,
            help="use a Windows subsystem executable (Windows only)")
    g.add_option("-v", "--version", type="string",
            dest="version_file", metavar="FILE",
            help="add a version resource from FILE to the exe "
                 "(Windows only)")
    g.add_option("-i", "--icon", type="string", dest="icon_file",
            metavar="FILE.ICO or FILE.EXE,ID",
            help="If FILE is an .ico file, add the icon to the final "
                 "executable. Otherwise, the syntax 'file.exe,id' to "
                 "extract the icon with the specified id "
                 "from file.exe and add it to the final executable")
    g.add_option("-m", "--manifest", type="string",
            dest="manifest", metavar="FILE or XML",
            help="add manifest FILE or XML to the exe "
                 "(Windows only)")
    g.add_option("-r", "--resource", type="string", default=[], dest="resources",
            metavar="FILE[,TYPE[,NAME[,LANGUAGE]]]", action="append",
            help="add/update resource of the given type, name and language "
                 "from FILE to the final executable. FILE can be a "
                 "data file or an exe/dll. For data files, atleast "
                 "TYPE and NAME need to be specified, LANGUAGE defaults "
                 "to 0 or may be specified as wildcard * to update all "
                 "resources of the given TYPE and NAME. For exe/dll "
                 "files, all resources from FILE will be added/updated "
                 "to the final executable if TYPE, NAME and LANGUAGE "
                 "are omitted or specified as wildcard *."
                 "Multiple resources are allowed, using this option "
                 "multiple times.")

    # Build.py options
    g = parser.add_option_group('Build options')
    g.add_option('--buildpath', default=os.path.join('SPECPATH', 'build',
            'pyi.TARGET_PLATFORM', 'SPECNAME'),
            help='Buildpath (default: %default)')
    g.add_option('-y', '--noconfirm',
            action="store_true", default=False,
            help='Remove output directory (default: %s) without '
                 'confirmation' % os.path.join('SPECPATH', 'dist'))

    main(parser)

