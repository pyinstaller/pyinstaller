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

import os
import sys


def gettemp(basename):
    """
    Get the path to a temp file previously written by the temp runner.
    Useful to compare results between running in interpreter and running frozen.
    """
    exec_dir = os.path.dirname(sys.executable)
    # onedir mode:
    # tmpdir
    # ├── python_exe.build
    # ├── build
    # └── dist
    #     └── appname
    #         └── appname.exe
    file_onedir = os.path.join(exec_dir, '..', '..', basename)
    # onefile mode:
    # tmpdir
    # ├── python_exe.build
    # ├── build
    # └── dist
    #     └── appname.exe
    file_onefile = os.path.join(exec_dir, '..', basename)

    if os.path.exists(file_onedir):
        return file_onedir
    else:
        return file_onefile
