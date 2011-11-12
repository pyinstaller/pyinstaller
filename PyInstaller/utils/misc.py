#
# Copyright (C) 2005-2011, Giovanni Bajo
# Based on previous work under copyright (c) 2002 McMillan Enterprises, Inc.
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

"""
This module is for the miscellaneous routines which do not fit somewhere else.
"""

import glob
import os


def dlls_in_subdirs(directory):
    """Returns *.dll, *.so, *.dylib in given directories and subdirectories."""
    files = []
    for root, dirs, files in os.walk(directory):
        files.extend(dlls_in_dir(root))


def dlls_in_dir(directory):
    """Returns *.dll, *.so, *.dylib in given directory."""
    files = []
    files.extend(glob.glob(os.path.join(directory, '*.so')))
    files.extend(glob.glob(os.path.join(directory, '*.dll')))
    files.extend(glob.glob(os.path.join(directory, '*.dylib')))
    return files
