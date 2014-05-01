#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
pywin32 module supports frozen mode. In frozen mode it is looking
in sys.path for file pythoncomXX.dll. Include the pythoncomXX.dll
as a data file. The path to this dll is contained in __file__
attribute.
"""

import os.path
from PyInstaller.hooks.hookutils import get_module_file_attribute

def hook(mod):
    pth = get_module_file_attribute('pythoncom')
    name = os.path.basename(pth)
    mod.binaries.extend([(name, pth, 'BINARY')])
    return mod
