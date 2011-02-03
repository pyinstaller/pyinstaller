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

import PyInstaller
import PyInstaller.makespec
import PyInstaller.lib.pyi_optparse as optparse

import os

p = optparse.OptionParser(
    usage="python %prog [opts] <scriptname> [<scriptname> ...]"
)
p.add_option('-C', '--configfile',
             default=PyInstaller.DEFAULT_CONFIGFILE,
             help='Name of configfile (default: %default)')

g = p.add_option_group('What to generate')
g.add_option("-F", "--onefile", dest="freeze",
             action="store_true", default=False,
             help="create a single file deployment")
g.add_option("-D", "--onedir", dest="freeze",
             action="store_false",
             help="create a single directory deployment (default)")
g.add_option("-o", "--out",
             dest="workdir", metavar="DIR",
             help="generate the spec file in the specified directory "
                  "(default: current directory")
g.add_option("-n", "--name",
             help="name to assign to the project "
                  "(default: first script's basename)")

g = p.add_option_group('What to bundle, where to search')
g.add_option("-p", "--paths", default=[], dest="pathex",
             metavar="DIR", action="append",
             help="set base path for import (like using PYTHONPATH). "
                  "Multiple directories are allowed, separating them "
                  "with %s, or using this option multiple times"
                  % repr(os.pathsep))
g.add_option("-K", "--tk", action="store_true",
             help="include TCL/TK in the deployment")
g.add_option("-a", "--ascii", action="store_true",
             help="do NOT include unicode encodings "
                  "(default: included if available)")

g = p.add_option_group('How to generate')
g.add_option("-d", "--debug", action="store_true",
             help="use the debug (verbose) build of the executable")
g.add_option("-s", "--strip", action="store_true",
             help="strip the exe and shared libs "
                  "(don't try this on Windows)")
g.add_option("-X", "--upx", action="store_true", default=True,
             help="use UPX if available (works differently between "
                  "Windows and *nix)")
#p.add_option("-Y", "--crypt", metavar="FILE",
#             help="encrypt pyc/pyo files")

g = p.add_option_group('Windows specific options')
g.add_option("-c", "--console", "--nowindowed", dest="console",
             action="store_true",
             help="use a console subsystem executable (Windows only) "
                  "(default)")
g.add_option("-w", "--windowed", "--noconsole", dest="console",
             action="store_false", default=True,
             help="use a Windows subsystem executable (Windows only)")
g.add_option("-v", "--version",
             dest="version_file", metavar="FILE",
             help="add a version resource from FILE to the exe "
                  "(Windows only)")
g.add_option("-i", "--icon", dest="icon_file",
             metavar="FILE.ICO or FILE.EXE,ID",
             help="If FILE is an .ico file, add the icon to the final "
                  "executable. Otherwise, the syntax 'file.exe,id' to "
                  "extract the icon with the specified id "
                  "from file.exe and add it to the final executable")
g.add_option("-m", "--manifest", metavar="FILE or XML",
             help="add manifest FILE or XML to the exe "
                  "(Windows only)")
g.add_option("-r", "--resource", default=[], dest="resources",
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

opts, args = p.parse_args()

# Split pathex by using the path separator
temppaths = opts.pathex[:]
opts.pathex = []
for p in temppaths:
    opts.pathex.extend(string.split(p, os.pathsep))

if not args:
    p.error('Requires at least one scriptname file')

name = PyInstaller.makespec.main(args, **opts.__dict__)
print "wrote %s" % name
print "now run Build.py to build the executable"
