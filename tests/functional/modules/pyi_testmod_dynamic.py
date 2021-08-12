#-----------------------------------------------------------------------------
# Copyright (c) 2005-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""
When frozen, a module that dynamically recreates itself at runtime (by replacing itself in sys.modules) should be
returned by __import__ statement.

This example should return True:
    >>> sys.modules[<dynamic_module>] is __import__(<dynamic_module>)
    True
"""

import sys
import types

# The DynamicModule should override this attribute.
foo = None


class DynamicModule(types.ModuleType):
    __file__ = __file__

    def __init__(self, name):
        super().__init__(name)
        self.foo = "A new value!"


# Replace module 'pyi_testmod_dynamic' by class DynamicModule.
sys.modules[__name__] = DynamicModule(__name__)
