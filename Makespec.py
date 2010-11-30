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
#TODO: resolving the dependence of len(resourcesPaths) with len(scripts)
common_part = """# -*- mode: python -*-
#(i) This file was automatically genereted by the Makespec.py

###########################
### Edit to your liking

names_of_exes = %(exenames)s
paths_to_exes = %(pathex)s

build_dir = '%(builddir)s'
dist_dir = '%(distdir)s'

exeIcon = ""
useConsole = True #on Windows set False if you want to use the subsystem executable
exeManifest = ""
exeVersion = ""

# Set here your resources paths as strings
#  If you don't set paths, PyInstaller won't be able to find them
resourcesPaths = %(resources)s
#   ("/where/to/find","/where/to/put")
#   ("/path/to/images","../relative/path/to/images")
#   ("/path/to/fonts","/my/home/project/fonts")
#   ("/path/to/configfiles","./config/files")
#   ("/these/are/only/examples","../../this/too")

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
        data = data + [(os.path.join(root, filename).replace(exploring_path, final_path, 1),
            os.path.join(root, filename), 'DATA') for filename in files]
    return data

home_paths=%(home_paths)s
scripts=%(scripts)s

%(marker)s
"""


onedir_tpl = """
if useTk:
    home_paths = home_paths + [
        os.path.join(HOMEPATH, "support", "useTK.py"),
        os.path.join(HOMEPATH, "support", "unpackTK.py"),
        os.path.join(HOMEPATH, "support", "removeTK.py")]

a = Analysis(
    home_paths + scripts,
    pathex=paths_to_exes)

for src, dest in resourcesPaths[0]:
    a.datas.extend(collectResources(src, dest))

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=1,
    name=os.path.join(build_dir, names_of_exes[0]),
    debug=useDebug,
    strip=useStrip,
    upx=useUPX,
    console=useConsole,
    icon=exeIcon,
    manifest=exeManifest,
    version=exeVersion)

tkTree = []
if useTk:
    tkTree.extend(TkTree())

coll = COLLECT(
    tkTree,
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=useStrip,
    upx=useUPX,
    name=dist_dir)
"""

onefile_tpl = """
if useTk:
    home_paths = home_paths + [os.path.join(HOMEPATH, "support", "useTK.py")]

a = Analysis(
    home_paths + scripts,
    pathex=paths_to_exes)

for src, dest in resourcesPaths[0]:
    a.datas.extend(collectResources(src, dest))

pyz = PYZ(a.pure)

tkPKG = []
if useTk:
    tkPKG.extend(TkPKG())

exe = EXE(
    tkPKG,
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name=dist_dir,
    debug=useDebug,
    strip=useStrip,
    upx=useUPX,
    console=useConsole,
    icon=exeIcon,
    manifest=exeManifest,
    version=exeVersion)
"""

merge_onedir_tpl = """
if useTk:
    home_paths = home_paths + [
        os.path.join(HOMEPATH, "support", "useTK.py"),
        os.path.join(HOMEPATH, "support", "unpackTK.py"),
        os.path.join(HOMEPATH, "support", "removeTK.py")]

an = []
tuples = []
scripts_count = len(scripts)

for i in range(scripts_count):
    a = Analysis(home_paths + [scripts[i]], pathex=paths_to_exes)
    an.append(a)
    tuples.append((a, names_of_exes[i], dist_dir))

MERGE(*tuples)

an_binaries = []
an_zipfiles = []
an_datas = []
for i in range(scripts_count):
    an_binaries.extend(an[i].binaries)
    an_zipfiles.extend(an[i].zipfiles)
    an_datas.extend(an[i].datas)
    for src, dest in resourcesPaths[i]:
        an_datas.extend(collectResources(src, dest))

exes = []
for i in range(scripts_count):
    pyz = (an[i].pure)
    exes.append(EXE(
        pyz,
        an[i].scripts,
        an[i].dependencies,
        exclude_binaries=1,
        name=os.path.join(build_dir, names_of_exes[i]),
        debug=useDebug,
        strip=useStrip,
        upx=useUPX,
        console=useConsole,
        icon=exeIcon,
        manifest=exeManifest,
        version=exeVersion))

tkTree = []
if useTk:
    tkTree.extend(TkTree())

coll = COLLECT(
    tkTree,
    an_binaries,
    an_zipfiles,
    an_datas,
    *exes,
    strip=useStrip,
    upx=useUPX,
    name=dist_dir)
"""

merge_onefile_tpl = """
if useTk:
    home_paths = home_paths + [
        os.path.join(HOMEPATH, "support", "useTK.py"),
        os.path.join(HOMEPATH, "support", "unpackTK.py"),
        os.path.join(HOMEPATH, "support", "removeTK.py")]

an = []
tuples = []
scripts_count = len(scripts)

for i in range(scripts_count):
    a = Analysis(home_paths + [scripts[i]], pathex=paths_to_exes)
    an.append(a)
    tuples.append((a, names_of_exes[i], dist_dir))

MERGE(*tuples)

an_binaries = []
an_zipfiles = []
an_datas = []
for i in range(scripts_count):
    for src, dest in resourcesPaths[i]:
        an[i].datas.extend(collectResources(src, dest))

tkPKG = []
if useTk:
    tkPKG.extend(TkPKG())

for i in range(len(scripts)):
    pyz = (an[i].pure)
    EXE(
        tkPKG,
        pyz,
        an[i].scripts,
        an[i].binaries,
        an[i].zipfiles,
        an[i].datas,
        an[i].dependencies,
        exclude_binaries=1,
        name=os.path.join(build_dir, names_of_exes[i]),
        debug=useDebug,
        strip=useStrip,
        upx=useUPX,
        console=useConsole,
        icon=exeIcon,
        manifest=exeManifest,
        version=exeVersion)
"""
marker = "### DO_NOT_REMOVE_THIS_MARKER"
HOME = os.path.abspath(os.path.dirname(sys.argv[0]))

def stringfyHomePaths(hp_list):
    string = '['
    for path in hp_list:
        string = string + "os.path.join(HOMEPATH, '" + path + "'), "
    string = string + ']'
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
    home_paths.insert(0, os.path.join("support", "_mountzlib.py"))

    home_paths = stringfyHomePaths(home_paths)

    pathex = [workingdir]

    options = {
        "exenames"  : options["exenames"],
        "pathex"    : pathex,
        "home_paths": home_paths,
        "scripts"   : scripts,
        "distdir"   : os.path.join("dist", options["exenames"][0]),
        "builddir"  : os.path.join("build", "pyi." + config["target_platform"], options["exenames"][0]),
        "onedir"    : options["onedir"],
        "onefile"   : not options["onedir"],
        "merge"     : options["merge"],
        "marker"    : marker,
        "resources" : [[]]*len(scripts)}

    specfile_name = options["exenames"][0] + ".spec"
    specfile = open(specfile_name, 'w')

    if config["target_platform"][:3] == "win" or \
       config["target_platform"] == "cygwin":
        for i in range(len(options["exenames"])):
            options["exenames"][i] = options["exenames"][i] + ".exe"

    if options["merge"]:
        if options["onedir"]:
            specfile.write((common_part + merge_onedir_tpl) % options)
        else:
            specfile.write((common_part + merge_onefile_tpl) % options)
    elif options["onedir"]:
        specfile.write((common_part + onedir_tpl) % options)
    else:
        specfile.write((common_part + onefile_tpl) % options)

def switchSpecDeployment(specfile_name, specfilenew_name, is_onedir):
    specfile_content = open(specfile_name, 'r').read()

    marker_pos = specfile_content.rfind(marker)
    if marker_pos == -1:
        raise SystemExit("Unable to find the marker. Abort!")

    marker_pos = marker_pos + len(marker)
    specfile_content = specfile_content[:marker_pos]

    if is_onedir:
        specfile_content = specfile_content + onedir_tpl
    else:
        specfile_content = specfile_content + onefile_tpl

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
        "-M", "--merge", dest="merge", action="store_true", default=False,
        help="Create a group of interdependent packages")

    opts, args = parser.parse_args()
    opts = opts.__dict__

    if not args:
        parser.error('Requires at least one scriptname file')

    name, filetype = os.path.splitext(os.path.basename(args[0]))

    exenames = []
    if opts["merge"]:
        for script in args:
            exenames.append(os.path.splitext(os.path.basename(script))[0])
    else:
        exenames = [name]

    opts["exenames"] = exenames

    if filetype == ".spec":
        if len(args) > 1:
            parser.error("Too many arguments. Give only one spec at time")
        switchSpecDeployment(name + filetype, opts["exenames"][0] + filetype, opts["onedir"])
    elif filetype == ".py":
        for filename in args:
            if not filename.endswith(filetype):
                parser.error("Arguments must be all python scripts (*.py)")
            if not open(filename):
                parser.error("File %s not found" % filename)
        createSpecFile(args, opts)
    else:
        parser.error("Give in input .py or .spec files only")


    if opts["onedir"]:
        dep_mode = "onedir"
    else:
        dep_mode = "onefile"

    print "%s has been wrote in %s mode" % (opts["exenames"][0] + ".spec", dep_mode)
    print "Now you can edit it and run the Build.py"
