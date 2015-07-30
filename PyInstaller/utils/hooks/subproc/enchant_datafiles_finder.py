#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import os
import enchant

def _win32_data_files():
    # This is basically a copy of enchant.utils.win32_data_files as of
    # release 1.6.0. We use this as a fallback for older versions of
    # enchant which do not have this function.
    # enchant is licenced under LGPL.
    dataDirs = ("share/enchant/myspell","share/enchant/ispell","lib/enchant")
    mainDir = os.path.abspath(os.path.dirname(enchant.__file__))
    dataFiles = []
    for dataDir in dataDirs:
        files = []
        fullDir = os.path.join(mainDir,os.path.normpath(dataDir))
        for fn in os.listdir(fullDir):
            fullFn = os.path.join(fullDir,fn)
            if os.path.isfile(fullFn):
                files.append(fullFn)
        dataFiles.append((dataDir,files))
    return dataFiles

try:
    from enchant.utils import win32_data_files
except:
    # fall back to the function above
    win32_data_files = _win32_data_files

print(win32_data_files())
