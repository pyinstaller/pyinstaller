#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import os, sys

def gettemp(basename):
    """
    Get the path to a temp file previously written by the temp runner. Useful to
    compare results between running in interpreter and running frozen.
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
