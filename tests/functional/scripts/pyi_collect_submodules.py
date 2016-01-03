#-----------------------------------------------------------------------------
# Copyright (c) 2005-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# This is designed to test the operation of PyInstaller.utils.hook.collect_submodules. To do so:
#
# 1. It imports the dummy module pyi_collect_submodules_mod, which contains nothing.
import pyi_collect_submodules_mod
# 2. This causes hook-pyi_collect_submodules_mod.py to be run, which collects some dummy submodules. In this case, it collects from modules/pyi_testmod_relimp.
# 3. Therefore, we should be able to find hidden imports under pyi_testmod_relimp.
__import__('pyi_testmod_relimp.B.C')
