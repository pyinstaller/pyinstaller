#-----------------------------------------------------------------------------
# Copyright (c) 2005-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

# PYTHONHOME (sys.prefix) has to be same as sys._MEIPASS.

import sys

print(('sys._MEIPASS: ' + sys._MEIPASS))
print(('sys.prefix: ' + sys.prefix))
print(('sys.exec_prefix: ' + sys.exec_prefix))

if not sys.prefix == sys._MEIPASS:
    raise SystemExit('sys.prefix is not set to path as in sys._MEIPASS.')
if not sys.exec_prefix == sys._MEIPASS:
    raise SystemExit('sys.exec_prefix is not set to path as in sys._MEIPASS.')
