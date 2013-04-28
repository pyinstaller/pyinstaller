#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import os
import matplotlib
import sys
import tempfile


# In frozen state rthook should force matplotlib to create config directory
# in temp directory and not $HOME/.matplotlib.
configdir = os.environ['MPLCONFIGDIR']
print('MPLCONFIGDIR: %s' % configdir)
if not configdir.startswith(tempfile.gettempdir()):
    raise SystemExit('MPLCONFIGDIR not pointing to temp directory.')


# matplotlib data directory should point to sys._MEIPASS.
datadir = os.environ['MATPLOTLIBDATA']
print('MATPLOTLIBDATA: %s' % datadir)
if not datadir.startswith(sys._MEIPASS):
    raise SystemExit('MATPLOTLIBDATA not pointing to sys._MEIPASS.')
