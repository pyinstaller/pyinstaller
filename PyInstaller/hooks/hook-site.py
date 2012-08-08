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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA


# Replace the code of real 'site' module by fake code doing nothing.
#
# The real 'site' does some magic to find paths to other possible
# Python modules. We do not want this behaviour for frozen applications.
#
# Fake 'site' makes PyInstaller to work with distutils and to work inside
# virtualenv environment.


import os

import PyInstaller


def hook(mod):
    # Replace mod by fake 'site' module.
    pyi_dir = os.path.abspath(os.path.dirname(PyInstaller.__file__))
    fake_file = os.path.join(pyi_dir, 'fake', 'fake-site.py')
    new_code_object = PyInstaller.utils.misc.get_code_object(fake_file)
    mod = PyInstaller.depend.modules.PyModule('site', fake_file, new_code_object)
    return mod
