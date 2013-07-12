#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# See ticket #27: historically, PyInstaller was catching all errors during imports...
try:
	import error_during_import2
except KeyError:
	print "OK"
else:
	raise RuntimeError("failure!")

