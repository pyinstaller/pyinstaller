#!/usr/bin/env python
"""
Suffix definitions for cross platform builds.
"""
# Copyright (C) 2008 Hartmut Goebel <h.goebel@goebel-consult.de>
# Licence: GNU General Public License version 3 (GPL v3)
#
# This file is part of PyInstaller <http://www.pyinstaller.org>
#
# pyinstaller is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyinstaller is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import imp
import sys

__all__ = ['get_suffixes']

# todo: complete this list for all available platforms
SUFFIXES = {
    'win32': (
        (".py",  "U",  imp.PY_SOURCE),
        (".pyw", "U",  imp.PY_SOURCE),
        (".pyc", "rb", imp.PY_COMPILED),
        (__debug__ and "_d.pyd" or ".pyd", "rb", imp.C_EXTENSION),
        (__debug__ and "_d.dll" or ".dll", "rb", imp.C_EXTENSION),
        ),
    }

def get_suffixes(target_platform=None):
    if target_platform == sys.platform:
        return imp.get_suffixes()
    # per default use the values from imp.get_suffixes
    return SUFFIXES.get(target_platform, None) or imp.get_suffixes()
