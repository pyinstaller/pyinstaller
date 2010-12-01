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
public_tpl = """# -*- mode: python -*-
#(ii) This file was automatically genereted by the Makespec.py

#####################################################
### (PUBLIC SPACE) Edit to your liking

# A list with the names of all the executables to build
names_of_exes = %(exenames)s

# An optional list of paths to be searched before sys.path
paths_to_src = %(pathex)s

# A list of lists of scripts. Nth list are relative to the Nth executable in 'names_of_exes'
# Every list into 'scripts' contains the scripts to be analyzed for a specific executable
scripts=%(scripts)s

# This list contains modules relative to the HOMEPATH.
# HOMEPATH is the system Python path
home_paths=%(home_paths)s

# You can add more modules in here. Every list is positionally relative
# to the executable in 'names_of_exes'.
# Modules must be written as a tuple:
#   ("nameOfModule", "nameOfModule.pyc", "PYMODULE")
# where the constant string 'PYMODULE' specifies to PyInstaller that is a module
more_pyz=%(voidlist)s

# This is the working directory where PyInstaller will build the executables
build_dir = '%(builddir)s'

# This is the directory where PyInstaller will deploy you final package
dist_dir = '%(distdir)s'

# This is the the icon file to use for the executable (Windows only)
exes_icon = %(voidlist)s

# This is the manifest file to use for the executable (Window only)
exes_manifest = %(voidlist)s

#This is the version file to use for the executable (Windows only)
exes_version = %(voidlist)s

# Set here your resources paths
# Nth list are relative to the Nth executable in 'names_of_exes'
# A resource must be written as a tuple:
#   ("/where/to/find","/where/to/put")
# where the first element is the path to search for take data and
# the second is the path where to put the data (it should be relative to the 'dist_dir')
resources_paths = %(voidlist)s

# Set False in Windows if you want to use the subsystem executable
use_console = True

# Set True if you want to enable the verbose mode running the executable
use_debug = False

# Set True if you want to remove the Debug symbols from the ELF executable (UNIX only)
use_strip = True

# Set True if you want UPX Packer (useful for Windows). If you are uncertain, leave True
use_UPX = True

# Set True if you want to include Tcl/Tk in you final package
use_tk = False

%(marker)s
"""

onedir_tpl = """
#####################################################
### (PRIVATE SPACE) Only for PyInstaller eyes
#
#(!!) Edit with *caution*
#(ii) For more information take a look to the documentation
#     on www.pyinstaller.org

def collect_resources(exploring_path, final_path):
    data = []
    for root, dirs, files in os.walk(exploring_path):
        data = data + [(os.path.join(root, filename).replace(exploring_path, final_path, 1),
            os.path.join(root, filename), 'DATA') for filename in files]
    return data

if use_tk:
    home_paths = home_paths + [os.path.join(HOMEPATH, "support", "useTK.py")]

an = []
tuples = []

for i in range(len(names_of_exes)):
    an.append(Analysis(home_paths + scripts[i], pathex=paths_to_src))
    tuples.append((an[i], os.path.splitext(names_of_exes[i])[0], names_of_exes[i]))
    for src, dest in resources_paths[i]:
        an[i].datas.extend(collect_resources(src, dest))

MERGE(*tuples)

an_binaries = []
an_zipfiles = []
an_datas = []
exes = []

for i in range(len(an)):
    an_binaries.extend(an[i].binaries)
    an_zipfiles.extend(an[i].zipfiles)
    an_datas.extend(an[i].datas)
    pyz = PYZ(an[i].pure + more_pyz[i])
    exes.append(EXE(
        pyz,
        an[i].scripts,
        an[i].dependencies,
        exclude_binaries=1,
        name=os.path.join(build_dir, names_of_exes[i]),
        debug=use_debug,
        strip=use_strip,
        upx=use_UPX,
        console=use_console,
        icon=exes_icon[i],
        manifest=exes_manifest[i],
        version=exes_version[i]))

tk_tree = []
if use_tk:
    tk_tree.extend(TkTree())

COLLECT(
    tk_tree,
    an_binaries,
    an_zipfiles,
    an_datas,
    *exes,
    strip=use_strip,
    upx=use_UPX,
    name=dist_dir)
"""

onefile_tpl = """
##############################
### Only for PyInstaller eyes
#
#(!) Edit with *caution*
#(i) For more information take a check out the documentation
#    on www.pyinstaller.org

def collect_resources(exploring_path, final_path):
    data = []
    for root, dirs, files in os.walk(exploring_path):
        data = data + [(os.path.join(root, filename).replace(exploring_path, final_path, 1),
            os.path.join(root, filename), 'DATA') for filename in files]
    return data

if use_tk:
    home_paths = home_paths + [
        os.path.join(HOMEPATH, "support", "useTK.py"),
        os.path.join(HOMEPATH, "support", "unpackTK.py"),
        os.path.join(HOMEPATH, "support", "removeTK.py")]

an = []
tuples = []

for i in range(len(names_of_exes)):
    an.append(Analysis(home_paths + scripts[i], pathex=paths_to_src))
    tuples.append((an[i], os.path.splitext(names_of_exes[i])[0], names_of_exes[i]))
    for src, dest in resources_paths[i]:
        an[i].datas.extend(collect_resources(src, dest))

MERGE(*tuples)

tk_PKG = []
if use_tk:
    tk_PKG.extend(TkPKG())

for i in range(len(an)):
    pyz = PYZ(an[i].pure + more_pyz[i])
    EXE(
        tk_PKG,
        pyz,
        an[i].scripts,
        an[i].binaries,
        an[i].zipfiles,
        an[i].datas,
        an[i].dependencies,
        name=os.path.join(dist_dir, names_of_exes[i]),
        debug=use_debug,
        strip=use_strip,
        upx=use_UPX,
        console=use_console,
        icon=exes_icon[i],
        manifest=exes_manifest[i],
        version=exes_version[i])
"""
marker = "### DO_NOT_REMOVE_THIS_MARKER"
HOME = os.path.abspath(os.path.dirname(sys.argv[0]))

def stringfy_home_paths(hp_list):
    string = '['
    for path in hp_list:
        string = string + "os.path.join(HOMEPATH, '" + path + "'), "
    string = string + ']'
    return string

def create_spec_file(scripts, options):
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

    home_paths = stringfy_home_paths(home_paths)

    pathex = [workingdir]

    options = {
        "exenames"  : options["exenames"],
        "pathex"    : pathex,
        "home_paths": home_paths,
        "distdir"   : os.path.join("dist", options["exenames"][0]),
        "builddir"  : os.path.join("build", "pyi." + config["target_platform"], options["exenames"][0]),
        "onedir"    : options["onedir"],
        "onefile"   : not options["onedir"],
        "merge"     : options["merge"],
        "marker"    : marker,
        "voidlist"  : [[]]*len(options["exenames"])}

    options["scripts"] = [[]]*len(options["exenames"])
    if options["merge"]:
        options["scripts"][0] = scripts
    else:
        for i in range(len(options["scripts"])):
            options["scripts"][i].append(scripts[i])

    specfile_name = options["exenames"][0] + ".spec"
    specfile = open(specfile_name, 'w')

    if config["target_platform"][:3] == "win" or \
       config["target_platform"] == "cygwin":
        for i in range(len(options["exenames"])):
            options["exenames"][i] = options["exenames"][i] + ".exe"

    if options["onedir"]:
        specfile.write((public_tpl + onedir_tpl) % options)
    else:
        specfile.write((public_tpl + onefile_tpl) % options)

def switch_spec_deployment(specfile_name, specfilenew_name, is_onedir):
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

    opts["exenames"] = []
    if opts["merge"]:
        for script in args:
            opts["exenames"].append(os.path.splitext(os.path.basename(script))[0])
    else:
        opts["exenames"].append(name)

    if filetype == ".spec":
        if len(args) > 1:
            parser.error("Too many arguments. Give only one spec at time")
        switch_spec_deployment(name + filetype, opts["exenames"][0] + filetype, opts["onedir"])
    elif filetype == ".py":
        for filename in args:
            if not filename.endswith(filetype):
                parser.error("Arguments must be all python scripts (*.py)")
            if not open(filename):
                parser.error("File %s not found" % filename)
        create_spec_file(args, opts)
    else:
        parser.error("Give in input .py or .spec files only")

    if opts["onedir"]:
        dep_mode = "onedir"
    else:
        dep_mode = "onefile"

    print "%s has been wrote in %s mode" % (opts["exenames"][0] + ".spec", dep_mode)
    print "Now you can edit it and run the Build.py"
