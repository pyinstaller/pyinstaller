# Copyright (C) 2006, Giovanni Bajo
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

# PIL's SpiderImagePlugin features a tkPhotoImage() method which imports
# ImageTk (and thus brings the whole Tcl/Tk library in).
# We cheat a little and remove the ImageTk import: I assume that if people
# are really using ImageTk in their application, they will also import it
# directly.
def hook(mod):
    for i in range(len(mod.imports)):
        if mod.imports[i][0] == "ImageTk":
            del mod.imports[i]
            break
    return mod
