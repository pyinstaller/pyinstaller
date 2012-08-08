#
# Copyright (C) 2009, Lorenzo Mancini
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


# Hook for PyOpenGL 3.x versions from 3.0.0b6 up. Previous versions have a
# plugin system based on pkg_resources which is problematic to handle correctly
# under pyinstaller; 2.x versions used to run fine without hooks, so this one
# shouldn't hurt.


from PyInstaller.compat import is_win, is_darwin
from PyInstaller.hooks.hookutils import opengl_arrays_modules


# PlatformPlugin performs a conditional import based on os.name and
# sys.platform. PyInstaller misses this so let's add it ourselves...
if is_win:
    hiddenimports = ['OpenGL.platform.win32']
elif is_darwin:
    hiddenimports = ['OpenGL.platform.darwin']
# Use glx for other platforms (Linux, ...)
else:
    hiddenimports = ['OpenGL.platform.glx']


# Arrays modules are needed too.
hiddenimports += opengl_arrays_modules()
