#-----------------------------------------------------------------------------
# Copyright (c) 2013-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


""" pkg2.a defines overridden and a_func """


def a_func():
    return "a_func from pkg2.a"
print("pkg2.a imported")
