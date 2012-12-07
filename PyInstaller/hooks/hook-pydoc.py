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


# Python module 'pydoc' causes the inclusion of Tcl/Tk library even in case
# of simple hello_world script. Most of the we do not want this behavior.
#
# This hook just removes this implicit dependency on Tcl/Tk.


def hook(mod):
    # Ignore 'Tkinter' to prevent inclusion of Tcl/Tk library.
    for i, m in enumerate(mod.imports):
        if m[0] == 'Tkinter':
            del mod.imports[i]
            break
    return mod
