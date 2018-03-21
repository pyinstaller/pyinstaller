# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

'''
Mock package defining and then deleting a global variable of the same name as a
mock submodule of this package.

This package is exercised by the `test_import_submodule_global_unshadowed`
functional test.
'''


submodule = 'And with strange aeons even death may die.'
'''
Global variable of the same name as a mock submodule of this package.

This variable's value is both arbitrary _and_ always ignored by this test.
'''


# Permit the "submodule" submodule to be imported. Since globals take precedence
# over submodules of the same name, failing to undefine this global would
# prevent this submodule from being imported.
#
# PyInstaller explicitly detects both the definition and undefinition of globals
# in the modules containing those globals -- namely, here. PyInstaller does not,
# however, detect either the definition or undefinition of these globals from
# other modules. In particular, PyInstaller ignores attempts to undefine this
# global from the functional test exercising this module (e.g., using
# "del pyi_testmod_submodule_global.submodule").
del submodule
