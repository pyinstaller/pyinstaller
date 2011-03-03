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
import sys, string

def hook(mod):
    names = sys.builtin_module_names
    if 'posix' in names:
        removes = ['nt', 'ntpath', 'dos', 'dospath', 'os2', 'mac', 'macpath',
                   'ce', 'riscos', 'riscospath', 'win32api', 'riscosenviron']
    elif 'nt' in names:
        removes = ['dos', 'dospath', 'os2', 'mac', 'macpath', 'ce', 'riscos',
                   'riscospath', 'riscosenviron',]
    elif 'os2' in names:
        removes = ['nt', 'dos', 'dospath', 'mac', 'macpath', 'win32api', 'ce',
                   'riscos', 'riscospath', 'riscosenviron',]
    elif 'dos' in names:
        removes = ['nt', 'ntpath', 'os2', 'mac', 'macpath', 'win32api', 'ce',
                   'riscos', 'riscospath', 'riscosenviron',]
    elif 'mac' in names:
        removes = ['nt', 'ntpath', 'dos', 'dospath', 'os2', 'win32api', 'ce',
                   'riscos', 'riscospath', 'riscosenviron',]
    for i in range(len(mod.imports)-1, -1, -1):
        nm = mod.imports[i][0]
        pos = string.find(nm, '.')
        if pos > -1:
            nm = nm[:pos]
        if nm in removes :
            del mod.imports[i]
    return mod
