#
# Copyright (C) 2012, Martin Zibricky
# Copyright (C) 2005, Giovanni Bajo
# Based on previous work under copyright (c) 2001, 2002 McMillan Enterprises, Inc.
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


hiddenimports = [
    # win32com client and server util
    # modules could be hidden imports
    # of some modules using win32com.
    # Included for completeness.
    'win32com.client.util',
    'win32com.server.util',
]


def hook(mod):
    # win32com module changes sys.path and wrapps win32comext modules.
    pth = str(mod.__path__[0])
    if os.path.isdir(pth):
        mod.__path__.append(
            os.path.normpath(os.path.join(pth, '..', 'win32comext')))
    return mod
