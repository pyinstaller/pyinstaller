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

import sys

def hook(mod):
    names = sys.builtin_module_names
    if 'posix' in names:
        removes = ['nt', 'dos', 'os2', 'mac', 'win32api']
    elif 'nt' in names:
        removes = ['dos', 'os2', 'mac']
    elif 'os2' in names:
        removes = ['nt', 'dos', 'mac', 'win32api']
    elif 'dos' in names:
        removes = ['nt', 'os2', 'mac', 'win32api']
    elif 'mac' in names:
        removes = ['nt', 'dos', 'os2', 'win32api']
    mod.imports = [m
                   for m in mod.imports
                   # if first part of module-name not in removes
                   if m[0].split('.', 1)[0] not in removes
    ]
    return mod
