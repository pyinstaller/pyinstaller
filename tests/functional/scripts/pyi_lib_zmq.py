#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import zmq
print(zmq.__version__)
print(zmq.zmq_version())
# This is a problematic module and might cause some issues.
import zmq.utils.strtypes
