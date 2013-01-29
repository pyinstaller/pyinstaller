#
# Copyright (C) 2013, Martin Zibricky
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


# PEP-302 import hooks specification contain section 'Optional Extensions to the Importer Protocol'

# This section is meant to be optional but the reality is different. Some Python modules
# (e.g. Flask) depends on implementation of these optional functions:
#
#   loader.is_package(fullmodname)
#   loader.get_code(fullmodname)
#   loader.get_source(fullmodname)
#
# This test tests the return values of these functions for importers from pyi_importers module.
# The return values should be same in frozen/unfrozen state. The only difference for frozen state
# is that in frozen state are used import hooks from pyi_importers.


import pkgutil

# Import just to get the necessary example modules.
import httplib
import sqlite3


# Use different types of modules. In frozen state there are import hooks
# for builtin, frozen and C extension modules.
builtin_mod = 'sys'
frozen_mod = 'httplib'
frozen_pkg = 'encodings'
c_extension_mod = '_sqlite3'


# BuiltinImporter class
print('Testing class BuiltinImporter.')
mod = builtin_mod
ldr = pkgutil.get_loader(mod)
assert ldr.is_package(mod) == False
assert ldr.get_code(mod) is None
assert ldr.get_source(mod) is None


# FrozenImporter class
print('Testing class FrozenImporter - module.')
mod = frozen_mod
ldr = pkgutil.get_loader(mod)
assert ldr.is_package(mod) == False
assert ldr.get_code(mod) is not None
assert ldr.get_source(mod) is None

print('Testing class FrozenImporter - package.')
mod = frozen_pkg
ldr = pkgutil.get_loader(mod)
assert ldr.is_package(mod) == True
assert ldr.get_code(mod) is not None
assert ldr.get_source(mod) is None


# CExtensionImporter class
print('Testing class CExtensionImporter.')
mod = c_extension_mod
ldr = pkgutil.get_loader(mod)
assert ldr.is_package(mod) == False
assert ldr.get_code(mod) is None
assert ldr.get_source(mod) is None
