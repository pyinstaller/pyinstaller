# Copyright (C) 2005, Giovanni Bajo
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# In addition to the permissions in the GNU General Public License, the
# authors give you unlimited permission to link or embed the compiled
# version of this file into combinations with other programs, and to
# distribute those combinations without any restriction coming from the
# use of this file. (The General Public License restrictions do apply in
# other respects; for example, they cover modification of the file, and
# distribution when not linked into a combine executable.)
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA

# PyOpenGL (specifically, OpenGL.__init__) reads a "version" text file
# containing the version number to export it as OpenGL.__version__. When
# packaging with PyInstaller, the 'version' file does not exist, and importing
# PyOpenGL results in an IOError.
# The (convoluted) solution is to override Python's builtin "open" with our
# own function which detects when "version" is opened and returns some fake
# content stream (through cStringIO).

__realopen__ = open

def myopen(fn, *args):
    if isinstance(fn, basestring):
        if fn.endswith("version") and ".pyz" in fn:
            # Restore original open, since we're almost done
            __builtins__.__dict__["open"] = __realopen__
            # Report a fake revision number. Anything would do since it's not
            # used by the library, but it needs to be made of four numbers
            # separated by dots.
            import cStringIO
            return cStringIO.StringIO("0.0.0.0")
    return __realopen__(fn, *args)

__builtins__.__dict__["open"] = myopen
