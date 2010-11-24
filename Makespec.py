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
### Edit to your liking

name_of_exe = '%(exename)s'
path_to_exe = %(pathex)s

build_dir = '%(builddir)s'
dist_dir = '%(distdir)s'

exeIcon = ""
useConsole = True #on Windows set False if you want to use the subsystem executable
exeManifest = ""
exeVersion = ""

# Set here your resources paths as strings
#  If you don't set paths, PyInstaller won't be able to find them
resourcesPaths = [
#   ("/where/to/find","/where/to/put")
#   ("/path/to/images","../relative/path/to/images")
#   ("/path/to/fonts","/my/home/project/fonts")
#   ("/path/to/configfiles","./config/files")
#   ("/these/are/only/examples","../../this/too")
]

useDebug = False
useStrip = True # Remove the Debug symbols from the ELF executable (only for UNIX)
useUPX = True # UPX Packer (useful for Windows)
useTk = False


##############################
### Only for PyInstaller eyes
#
#(!) Edit with *caution*
#(i) For more information take a check out the documentation
#    on www.pyinstaller.org

def collectResources(exploring_path, final_path):
    data = []
    for root, dirs, files in os.walk(exploring_path):
        data += [(os.path.join(root, filename).replace(exploring_path, final_path, 1),
            os.path.join(root, filename), 'DATA') for filename in files]
    return data

a = Analysis(
    %(home_paths)s +
    %(scripts)s,
    pathex=path_to_exe)

for src, dest in resourcesPaths:
    a.datas.extend(collectResources(src, dest))

pyz = PYZ(a.pure)

%(marker)s"""


onedir_tpl = """ Do not remove or edit this marker
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=1,
    name=os.path.join(build_dir, name_of_exe),
    debug=useDebug,
    strip=useStrip,
    upx=useUPX,
    console=useConsole,
    icon=exeIcon,
    manifest=exeManifest,
    version=exeVersion)

if useTk:
    useTk = []
    useTk.extend(TkTree())
else:
    useTk = []

coll = COLLECT(
    useTk,
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=useStrip,
    upx=useUPX,
    name=os.path.join(dist_dir, name_of_exe))
"""

onefile_tpl = """ Do not remove or edit this marker
if useTk:
    useTk = []
    useTk.extend(TkPKG())
else:
    useTk = []

exe = EXE(
    useTk,
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name=os.path.join(dist_dir, name_of_exe),
    debug=useDebug,
    strip=useStrip,
    upx=useUPX,
    console=useConsole,
    icon=exeIcon,
    manifest=exeManifest,
    version=exeVersion)
"""
marker = "###@O@_"
HOME = os.path.abspath(os.path.dirname(sys.argv[0]))

def stringfyHomePaths(hp_list):
    string = '['
    for path in hp_list:
        string += "os.path.join(HOMEPATH, '" + path + "'), "
    string += ']'
    return string

def createSpecFile(scripts, options):
    configfile_name = os.path.join(HOME, "config.dat")
    workingdir = os.getcwd()

    config = eval(open(configfile_name, 'r').read())

    if config["pythonVersion"] != sys.version:
        msg = """PyInstaller configfile and current Python version are incompatible.
            Please re-run Configure.py with this version."""
        raise SystemExit(msg)

    home_paths = []
    if config["hasUnicode"]:
        home_paths.insert(0, os.path.join("support", "useUnicode.py"))
    if not options["onedir"]:
        home_paths.insert(0, os.path.join("support", "unpackTK.py"))
        home_paths.append(os.path.join("support", "removeTK.py"))
    home_paths.insert(0, os.path.join("support", "_mountzlib.py"))
    home_paths.insert(0, os.path.join("support", "useTK.py"))

    home_paths = stringfyHomePaths(home_paths)

    pathex = [workingdir]

    options = {
        "exename"   : options["exename"],
        "pathex"    : pathex,
        "home_paths": home_paths,
        "scripts"   : scripts,
        "distdir"   : "dist",
        "builddir"  : os.path.join("build", "pyi." + config["target_platform"], options["exename"]),
        "onedir"    : options["onedir"],
        "onefile"   : not options["onedir"],
        "marker"    : marker}

    specfile_name = options["exename"] + ".spec"
    specfile = open(specfile_name, 'w')

    if config["target_platform"][:3] == "win" or \
       config["target_platform"] == "cygwin":
        options["exename"] += ".exe"

    if options["onedir"]:
        specfile.write((common_part + onedir_tpl) % options)
    else:
        specfile.write((common_part + onefile_tpl) % options)

def switchSpecDeployment(specfile_name, specfilenew_name, is_onedir):
    specfile_content = open(specfile_name, 'r').read()

    marker_pos = specfile_content.rfind(marker)
    if marker_pos == -1:
        raise SystemExit("Unable to find the marker. Abort!")

    marker_pos += len(marker)
    specfile_content = specfile_content[:marker_pos]

    if is_onedir:
        specfile_content += onedir_tpl
    else:
        specfile_content += onefile_tpl

    open(specfilenew_name, 'w').write(specfile_content)

if __name__ == '__main__':

    import pyi_optparse as optparse

    parser = optparse.OptionParser(
        usage = "usage: %prog [opts] <scriptname> [<scriptname> ...] | <specname>")

    parser.add_option(
        "-F", "--onefile", dest="onedir", action="store_false", default=True,
        help="Create a single file deployment")
    parser.add_option(
        "-D", "--onedir", dest="onedir", action="store_true", default=True,
        help="Create a single directory deployment")
    parser.add_option(
        "-n", "--name", dest="exename", action="store", type="string", nargs=1,
        help="The name to give to the executable")

    opts, args = parser.parse_args()
    opts = opts.__dict__


    # Check for parsing errors
    if not args:
        parser.error('Requires at least one scriptname file')

    name, filetype = os.path.splitext(os.path.basename(args[0]))
    if not opts["exename"]:
        opts["exename"] = name

    if filetype == ".spec":
        if len(args) > 1:
            parser.error("Too many arguments. Give only one spec at time")
        switchSpecDeployment(name + filetype, opts["exename"] + filetype, opts["onedir"])
    elif filetype == ".py":
        for filename in args:
            if not filetype in filename:
                parser.error("Arguments must be all python scripts (*.py)")
        createSpecFile(args, opts)
    else:
        parser.error("Give in input .py or .spec files only")


    if opts["onedir"]:
        dep_mode = "onedir"
    else:
        dep_mode = "onefile"

    print "%s has been wrote in %s mode" % (os.path.join(os.getcwd(), opts["exename"] + ".spec"), dep_mode)
    print "Now you can edit it and run the Build.py"
