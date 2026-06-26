#-----------------------------------------------------------------------------
# Copyright (c) 2013-2023, PyInstaller Development Team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: Apache-2.0
#-----------------------------------------------------------------------------


def _pyi_rthook():
    import os
    import sys

    # Set path to Tcl and Tk library directories, if they exist.
    # The directory names must match TCL_ROOTNAME and TK_ROOTNAME constants defined in `PyInstaller.utils.hooks.tcl_tk`.
    #
    # Usually, these library directories are collected by the build process, and the lack of directories should be
    # considered an error. However, there are also various scenarios where this is not the case; for example, system
    # Tcl/Tk framework being used on macOS, or a Windows build of Tcl/Tk 9 with DLL-embedded library .zip archives, and
    # so on. The build process should have more information about particular scenario, so an error should be raised
    # during build process as necessary.
    tcldir = os.path.join(sys._MEIPASS, '_tcl_data')
    tkdir = os.path.join(sys._MEIPASS, '_tk_data')

    if os.path.isdir(tcldir):
        os.environ["TCL_LIBRARY"] = tcldir

    if os.path.isdir(tkdir):
        os.environ["TK_LIBRARY"] = tkdir


_pyi_rthook()
del _pyi_rthook
