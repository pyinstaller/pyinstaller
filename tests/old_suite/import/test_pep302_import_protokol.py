#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


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

import sys
import pkgutil

# Import just to get the necessary example modules.
import compileall
import sqlite3

frozen = getattr(sys, 'frozen', False)

# Use different types of modules. In frozen state there are import hooks
# for builtin, frozen and C extension modules.
builtin_mod = 'sys'
frozen_mod = 'compileall'
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
if frozen:
    assert ldr.get_source(mod) is None
else:
    assert ldr.get_source(mod) is not None

print('Testing class FrozenImporter - package.')
mod = frozen_pkg
ldr = pkgutil.get_loader(mod)
assert ldr.is_package(mod) == True
assert ldr.get_code(mod) is not None
if frozen:
    assert ldr.get_source(mod) is None
else:
    assert ldr.get_source(mod) is not None

# CExtensionImporter class
print('Testing class CExtensionImporter.')
mod = c_extension_mod
ldr = pkgutil.get_loader(mod)
assert ldr.is_package(mod) == False
assert ldr.get_code(mod) is None
assert ldr.get_source(mod) is None
