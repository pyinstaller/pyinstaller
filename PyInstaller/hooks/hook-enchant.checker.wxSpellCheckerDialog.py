#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
# enchant.checker.wxSpellCheckerDialog causes pyinstaller to include
# whole gtk and wx libraries if they are installed. This module is
# thus ignored to prevent this.
"""

# TODO find better workaround
def hook(hook_api):
    # Workaround DOES NOT work with well with python 2.6
    # let's just disable it
    #return None
    pass
