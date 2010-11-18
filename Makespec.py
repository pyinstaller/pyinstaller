#!/usr/bin/env python
#
# Automatically build spec files containing a description of the project
#
# Copyright (C) 2010, Daniel Sanchez Iaizzo, codeverse@develer.com
# Based on previous work under copyright (c) 2002 McMillan Enterprises, Inc. and
# under copyright (c) 2005, Giovanni Bajo
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

# For Python 1.5 compatibility
try:
    True
except:
    True = (1 is 1)
    False = not True

# This is the part of the spec present in both onefile and onedir template
common_part = """# -*- mode: python -*-
#(i) This file was automatically genereted by the Makespec.py


###########################
### Edit it to your liking

name_of_exe = '%(exename)s'
path_to_exe = %(pathex)s

# Set here your resources paths as strings
#  If you don't set paths, PyInstaller won't be able to find them
resourcesPaths = [
#   ("/where/to/find","/where/to/put")
#   ("/path/to/images","../relative/path/to/images")
#   ("/path/to/fonts","/my/home/project/fonts")
#   ("/path/to/configfiles","./config/files")
#   ("/these/are/only/examples","../../this/too")
]

useDebug = False # set True or False

# Remove the Debug symbols from the ELF executable (only for UNIX)
useStrip = True # set True or False

# UPX Packer (good for Windows)
useUPX = True # set True or False

useTk = False # set True or False


##############################
### Only for PyInstaller eyes
#
#(!) Edit with *caution*
#(i) For more information take a check out the documentation
#    on www.pyinstaller.org

def collectResources(exploring_path, final_path):
    import os
    data = []
    exploring_path = os.path.normpath(exploring_path)
    final_path = os.path.normpath(final_path)
    if debug:
        print "Exploring the", os.path.basename(exploring_path), "directory in",\\
            os.path.dirname(exploring_path), "and moving all its content to",\\
            os.path.basename(final_path)
    for root, dirs, files in os.walk(exploring_path):
        data += [(os.path.join(root, filename).replace(exploring_path, final_path, 1),
            os.path.join(root, filename), 'DATA') for filename in files]
    if useDebug:
        for what_from, _, __ in data:
            print "Found", what_from
    return data

a = Analysis(
    %(scripts)s,
    pathex=path_to_exe)

pyz = PYZ(a.pure)
"""

onedir_tpl = """
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=1,
    name=os.path.join(%(builddir)s, name_of_exe),
    debug=useDebug,
    strip=useStrip
    upx=useUPX)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    [collectResources(src, dest) for src, dest in resourcesPaths],
    strip=useStrip,
    upx=useUPX,
    name=os.path.join(path_to_exe, name_of_exe)
"""

onefile_tpl = """
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [collectResources(src, dest) for src, dest in resourcesPaths],
    name=os.path.join(path_to_exe, name_of_exe),
    debug=useDebug,
    strip=useStrip,
    upx=useUPX)
"""

HOME = os.path.realpath(os.path.abspath(os.path.dirname(sys.argv[0])))

def makeHomePathVariable(path_suffix):
    return "os.path.join('HOMEPATH', '%s')" % path_suffix

def createSpecFile(exename, scripts, options):
    configfile = os.path.join(HOME, "config.dat")
    workingdir = os.getcwd()

    config = eval(open(configfile, 'r').read())
    if not config:
        msg = """"Unable to open %s: file missing or unreadable.
            Please run Configure.py before using PyInstaller""" % configfile
        raise SystemExit(msg)

    if config["pythonVersion"] != sys.version:
        msg = """PyInstaller configfile and current Python version are incompatible.
            Please re-run Configure.py with this version."""
        raise SystemExit(msg)

    home_paths = []
    if config["hasUnicode"]:
        home_paths.insert(0, os.path.join("support", "useUnicode.py"))
    home_paths.insert(0, os.path.join("support", "_mountzlib.py"))

    scripts = map(makeHomePathVariable, home_paths) + scripts

    pathex = [workingdir]
    print type(options), options
    options = {
        "exename"   : exename,
        "pathex"    : pathex,
        "scripts"   : scripts,
        "distdir"   : "dist",
        "builddir"  : os.path.join('build', 'pyi.' + config['target_platform'], exename),
        "onedir"    : options["onedir"],
        "onefile"   : not options["onedir"]}


    specfile_name = exename + ".spec"
    specfile = open(specfile_name, 'w')
    if not specfile:
        raise SystemExit("Unable to open %s" % specfile_name)

    if filetype == ".py":
        if options["onedir"]:
            specfile.write((common_part + onedir_tpl) % options)
        elif options["onefile"]:
            specfile.write((common_part + onefile_tpl) % options)
    elif filetype == ".spec":
        pass #TODO: Analyze the old_specfile and generating the new one

    return specfile_name


if __name__ == '__main__':

    import pyi_optparse as optparse

    parser = optparse.OptionParser(
        usage = "usage: %prog [--onefile | --onedir] <scriptname> [<scriptname> ...] | <specname>")

    parser.add_option(
        "-F", "--onefile", dest="onedir", action="store_false", default=True,
        help="Create a single file deployment")
    parser.add_option(
        "-D", "--onedir", dest="onedir", action="store_true", default=True,
        help="Create a single directory deployment")

    opts, args = parser.parse_args()
    opts = opts.__dict__

    # Check for parsing errors
    if not args:
        parser.error('Requires at least one scriptname file')

    name, filetype = os.path.splitext(os.path.basename(args[0]))

    if filetype == ".spec":
        if len(scripts) > 1:
            parser.error("Too many arguments. Give only one spec at time")

        old_specfile = open(name + ".spec", 'r')
        #TODO: Old spec parsing implementation

    elif filetype == ".py":
        for filename in args:
            if not filetype in filename:
                parser.error("Arguments must be all python scripts (*.py)")
    else:
        parser.error("Give in input .py or .spec files only")


    specfile_name = createSpecFile(name, args, opts)

    if opts["onedir"]:
        dep_mode = "onedir"
    else:
        dep_mode = "onefile"

    print "%s has been wrote in %s mode" % (os.path.join(os.getcwd(), specfile_name), dep_mode)
    print "Now you can edit it and run the Build.py"
