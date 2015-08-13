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
    data_dirs = ("share/enchant/myspell", "share/enchant/ispell", "lib/enchant")
    main_dir = os.path.abspath(os.path.dirname(enchant.__file__))
    data_files = []
    for data_dir in data_dirs:
        files = []
        full_dir = os.path.join(main_dir, os.path.normpath(data_dir))
        for fn in os.listdir(full_dir):
            full_fn = os.path.join(full_dir, fn)
            if os.path.isfile(full_fn):
                files.append(full_fn)
        data_files.append((data_dir, files))
    return data_files

try:
    from enchant.utils import win32_data_files
except:
    # fall back to the function above
    win32_data_files = _win32_data_files

print(win32_data_files())
