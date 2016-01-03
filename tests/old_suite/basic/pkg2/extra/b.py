#-----------------------------------------------------------------------------
# Copyright (c) 2013-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


""" b.py lives in extra, but shows as pkg2.b (and pkg1.b)"""

def b_func():
    return  "b_func from pkg2.b (pkg2/extra/b.py)"
