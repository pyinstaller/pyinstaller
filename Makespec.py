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
# if keywords True and False don't exist
# it sets them manually
try:
    True
except:
    True = (1 is 1)
    False = not True

# This is the part of the spec present both in onefile and in
# onedir template
# It is the part that the user has to edit on his own
common_part = """\
############################################################
# This file was automatically genereted by the Makespec.py #
############################################################

############################################################
def collectResources(exploring_path, final_path, debug=False):
    \"""
    collectResources(exploring_path, final_path, debug=False) ~> list
    This function returns a list of touples with all the path of the
    files found in the `exploring_path' directory and its sub-dir in the
    [(final_file, exploring_file, type), (..., ..., ...), ...] form where:
    final_file is the final filename including its path;
    exploring_file is the name of the file found including its path;
    type is the string 'DATA'
    \"""
    import os
    data = []

    exploring_path = os.path.normpath(exploring_path)
    final_path = os.path.normpath(final_path)

    if debug:
    print "Exploring the", os.path.basename(exploring_path), "directory in",
    os.path.dirname(exploring_path), "and moving all its content to",
    os.path.basename(final_path)

    for root, dirs, files in os.walk(exploring_path):
    data += [(os.path.join(root, filename).replace(exploring_path, final_path, 1),
    os.path.join(root, filename), 'DATA') for filename in files]

    if debug:
    (print "Found", filename[0]) for filename in data

    return data
############################################################

############################################################
### Edit it to your liking

# This is the name of your final executable
name_of_exe = '%(exename)s'

# This is the path where your executable and the relative
# data will be putted
path_to_exe = %(paths)s

# Set here your resources paths as strings
#  If you don't set paths, PyInstaller won't be able to find them
resourcesPaths = [
#   ("/where/to/find","/where/to/put")
#   ("/path/to/images","../relative/path/to/images")
#   ("/path/to/fonts","/my/home/project/fonts")
#   ("/path/to/configfiles","./config/files")
#   ("/these/are/only/examples","../../this/too")
]

# Do you want to use Debug during build and execution?
useDebug = True # set True or False

# Do you want to use the strip option?
#  This will remove the Debug symbols from the ELF executable
#  making it smaller (only for UNIX)
useStrip = False # set True or False

# Do you want to use UPX?
#  UPX is an executable packer that makes the executable
#  smaller. It is convenient especially under Windows
useUPX = True # set True or False


############################################################
### Only for PyInstaller eyes

#(!) Edit with caution
#(i) For more information take a check out the documentation
#    on www.pyinstaller.org

# The Analysis class takes in input the source files *.py
# and analyzes all the imports for including dependencies
# into the final package (!!include here the unfound python
# sources after the Build step!!)
a = Analysis(
    %(scripts)s,
    pathex=path_to_exe)

# The PYZ class takes the `pure' of the last Analysis object
# and generate the PYZ archive containing the pure python modules
pyz = PYZ(a.pure)
"""

# The OneDir template generate (as final package) a directory
# package containing the executable, the dynamic libraries and
# all the resources needed by the program
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
    strip=useStrip,
    upx=useUPX,
    name=os.path.join(path_to_exe, name_of_exe)
"""

# The OneFile template generate (as final package) an executable
# containing dynamic libraries, data resources, and the pure modules.
# When the executable will be launched
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

HOME = os.path.abspath(os.path.dirname(sys.argv[0]))

def createSpecFile(scripts, options):

    #configfile = os.path.join(HOME, "config.dat")
    configfile = "/home/codeverse/.pyinstaller/config.dat"

    try:
        config = eval(open(configfile, 'r').read())
    except IOError:
        raise SystemExit("Configfile is missing or unreadable. Please run Configure.py before building!")

    if config['pythonVersion'] != sys.version:
        print "The current version of Python is not the same with which PyInstaller was configured."
        print "Please re-run Configure.py with this version."
        raise SystemExit(1)

    exename, filetype = os.path.splitext(os.path.basename(scripts[0]))

    # Check for parsing errors
    if filetype == ".spec":
        if len(scripts) > 1:
            parser.error("Too many arguments. Give only one spec at time")

        try:
            old_specfile = open(exename + ".spec", 'r')
        except IOError as (errno, strerror):
            print "I/O error(%s): %s" % (errno, strerror)

    elif filetype == ".py":
        for filename in scripts:
            if not filetype in filename:
                parser.error("Arguments must be all python scripts (*.py)")
    else:
        parser.error("Give in input .py or .spec files only")


    dic = {
        "exename"   : exename,
        "paths"     : "blablabla",
        "scripts"   : scripts,
        "builddir"  : os.getcwd(),
        "onedir"    : options["onedir"],
        "onefile"   : not options["onedir"]}


    specfile = None
    specfile_name = exename + ".spec"
    count = 0
    while not specfile:
        try:
            specfile = open(specfile_name + ".spec", 'w')
        except:
            count += 1
            specfile_name = exename + str(count) + ".spec"


    if filetype == ".py":
        if dic["onedir"]:
            specfile.write((common_part + onedir_tpl) % dic)
        elif dic["onefile"]:
            specfile.write((common_part + onefile_tpl) % dic)

    specfile.close()

    return specfile_name


if __name__ == '__main__':

    import pyi_optparse as optparse

    # Creating an argument parser
    parser = optparse.OptionParser(
        usage = "usage: %prog [--onefile | --onedir] <scriptname> [<scriptname ...] | <specname>")

    parser.add_option(
        "-F", "--onefile", dest="onedir", action="store_false", default=True,
        help="Create a single file deployment")
    parser.add_option(
        "-D", "--onedir", dest="onedir", action="store_true", default=True,
        help="Create a single directory deployment")


    opts, args = parser.parse_args()
    opts = opts.__dict__

    if opts["onedir"]:
        dep_mode = "onedir"
    else:
        dep_mode = "onefile"

    if not args:
        parser.error('Requires at least one scriptname file')

    specfile_name = createSpecFile(args, opts)

    print "The spec file %s has been created in %s mode." % (os.path.join(os.getcwd(), specfile_name), dep_mode)
    print "Now you can edit it and run `Build.py %s'" % specfile_name
