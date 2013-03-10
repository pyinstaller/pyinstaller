#
# Copyright (C) 2012, Martin Zibricky
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA


# PYTHONHOME (sys.prefix) has to be same as sys._MEIPASS.

import sys


print('sys._MEIPASS: ' + sys._MEIPASS)
print('sys.prefix: ' + sys.prefix)
print('sys.exec_prefix: ' + sys.exec_prefix)

if not sys.prefix == sys._MEIPASS:
    raise SystemExit('sys.prefix is not set to path as in sys._MEIPASS.')
if not sys.exec_prefix == sys._MEIPASS:
    raise SystemExit('sys.exec_prefix is not set to path as in sys._MEIPASS.')
