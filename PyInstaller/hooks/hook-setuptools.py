#
# Copyright (C) 2011, Martin Zibricky
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

from PyInstaller import is_unix, is_darwin

hiddenimports = [
    # Test case import/test_zipimport2 fails during importing
    # pkg_resources or setuptools when module not present.
    'distutils.command.build_ext',
]

# Necessary for setuptools on Mac/Unix
if is_unix or is_darwin:
    hiddenimports.append('syslog')
