#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import pyi_testmod_relimp2.bar
import pyi_testmod_relimp2.bar.bar2


pyi_testmod_relimp2.bar.say_hello_please()
pyi_testmod_relimp2.bar.bar2.say_hello_please()
