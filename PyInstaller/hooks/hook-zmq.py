#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Hook for PyZMQ. Cython based Python bindings for messaging library ZeroMQ.
http://www.zeromq.org/
"""
import glob
import os



def hook(mod):
	global hiddenimports
	global datas
	hiddenimports = []

	modpath = mod.__path__[0]

	# Make sure we get the libzmq.pyd file which everything in pyzmq depends upon.
	datas = [(os.path.join(modpath, 'libzmq.pyd'), '')]

	extensions = ["*.py"]

	# sub-packages of zmq to add modules from
	path_mods = ["backend.cython", "backend.cffi"]
	for path_mod in path_mods:
		for extension in extensions:
			# Build the file path out of the dotted-notation stored in path_mods
			paths = path_mod.split(".")
			path = os.path.join(modpath, *[x for x in paths])

			# Get the files with the current extension
			for fn in glob.glob(os.path.join(path, extension)):
				fn = os.path.basename(fn)
				fn = os.path.splitext(fn)[0]

				# Add the found file to hiddenimports in dotted-notation
				hiddenimports.append('zmq.{}.'.format(path_mod) + fn)

	return mod
