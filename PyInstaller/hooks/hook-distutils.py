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


import distutils
import marshal
import os


def hook(mod):
    """
    Contributed by jkp@kirkconsulting.co.uk
    This hook checks for the distutils hacks present when using the 
    virtualenv package.
    """
    # Non-empty  means PyInstaller is running inside virtualenv.
    # Virtualenv overrides real distutils modules.
    if hasattr(distutils, 'distutils_path'):
        mod_path = os.path.join(distutils.distutils_path, '__init__.pyc')
        try:
            parsed_code = marshal.loads(open(mod_path, 'rb').read()[8:])
        except IOError:
            parsed_code = compile(open(mod_path[:-1], 'rU').read(), mod_path, 'exec')
        mod.__init__('distutils', mod_path, parsed_code)
    return mod
