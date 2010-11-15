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

# For Python 1.5 compatibility:
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
### Edit it to your liking

# This is the name of your final executable
name_of_exe = '%(exename)s'

# This is the path where your executable and the relative
# data will be putted
path_to_exe = %(pathex)s

# Set here your resources paths as strings
#  If you don't set paths, PyInstaller won't be able to find them
resourcesPaths = [
#	"/path/to/images",
#	"/path/to/fonts",
#	"/path/to/configfiles",
#	"/these/are/only/examples"
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
#(i) For more information take a look to the Makespec.README

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
	%(tktree)s exe,
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
	a.datas + importResources(...)
	name=os.path.join(path_to_exe, name_of_exe),
	debug=useDebug,
	strip=useStrip,
	upx=useUPX)
"""

# This is the implementation of the collectResources function
collectResources_def = """
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
	
	# Normalizing paths
	exploring_path = os.path.normpath(exploring_path)
	final_path = os.path.normpath(final_path)

	# If debug flag is activated it prints some information
	if debug is True:
		print "Exploring the", os.path.basename(exploring_path), "directory in",
			os.path.dirname(exploring_path), "and moving all its content to",
			os.path.basename(final_path)

	# This loop find every file in the `exploring_path' directory
	# and all its sub-directory
	for root, dirs, files in os.walk(exploring_path):
		data += [(os.path.join(root, filename).replace(exploring_path, final_path, 1),
				  os.path.join(root, filename), 'DATA') for filename in files]

	# If debug flag is activated it prints all the files found in exploring_path
	if debug is True:
		(print "Found", filename[0]) for filename in data
		
	return data
"""


if __name__ == '__main__':

	import argparse

	# This def is called at the time you pass an argument in the command
	# line as a script file
	# It checks if the argument is a valid script file or not
	def ScriptFileType(scriptfile):
		if not scriptfile.endswith(".py") or not open(scriptfile, 'w'):
			raise argparse.ArgumentTypeError(
				"%s file is not a valid python script file" % scriptfile)
		return scriptfile

	# This def is called at the time you pass an argument in the command
	# line as a spec file
	# It checks if the argument is a valid spec file or not
	def SpecFileType(specfile):
		if not specfile.endswith(".spec") or not open(specfile, "wr"):
			raise argparse.ArgumentTypeError(
				"%s file is not a valid spec file" % specfile)
		return specfile



	# Creating an argument parser
	parser = argparse.ArgumentParser(
		prog="Makespec.py",
		description="A sub-tool for creating the .spec file")
	

	# Adding arguments `scripts' and `specs'in a mutually exclusive group
	# You cannot give more then one element of a MEG at the command line
	# at the same time. Only one option at time is valid
	group = parser.add_mutually_exclusive_group()
	group.add_argument(
		"scripts", nargs='+', type=ScriptFileType,
		help="A python scripts that will be analyzed")
	group.add_argument(
		"specs", nargs='+', type=SpecFileType,
		help="A spec file to convert in a newer one")
	
	# Adding arguments `--onefile' and `--onedir' in a MEG
	# --onefile and --onedir arguments cannot coexist
	group = parser.add_mutually_exclusive_group()
	group.add_argument(
		"-F", "--onefile", action="store_true", default=False,
		help="Create a single file deployment")
	group.add_argument(
		"-D", "--onedir", action="store_true", default=True,
		help="Create a single directory deployment")

	# args contains the options given in the command line
	args = parser.parse_args()

	#if not args:
	#	parser.error('Requires at least one scriptname file')

	#name = apply(main, (args,), opts.__dict__)
	print "The spec file %s has been created." % name
	print "Now you can edit it and run `Build.py %s\'" % name
	

