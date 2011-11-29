# Copyright (C) 2009, Lorenzo Berni
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

import glob
import os
import PyInstaller
import PyInstaller.compat as compat

from hookutils import django_dottedstring_imports, find_django_root

python_path = compat.getenv("PYTHONPATH")

if python_path:
    python_path = os.pathsep.join([python_path] + PyInstaller.__pathex__)
else:
    python_path = os.pathsep.join(PyInstaller.__pathex__)

django_root_dirs = [find_django_root(path)
                    for path in python_path.split(os.pathsep)]

if not django_root_dirs:
    raise RuntimeError("No django root directory found. Please check your "
                       "pathex definition in the project spec file.")

if django_root_dirs[0] in PyInstaller.__pathex__:
    raise RuntimeError("The django root directory is defined in the pathex. "
                       "You have to define the parent directory instead of "
                       "the django root directory.")

compat.setenv("PYTHONPATH", python_path)

hiddenimports = [django_dottedstring_imports(root_dir)
                 for root_dir in django_root_dirs]


