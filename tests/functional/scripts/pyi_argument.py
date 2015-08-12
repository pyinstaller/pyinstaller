#-----------------------------------------------------------------------------
# Copyright (c) 2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import sys
assert sys.argv[1] == "--argument", "sys.argv was %s, expected %s" % (sys.argv, sys.argv[:0] + ["--argument"])
