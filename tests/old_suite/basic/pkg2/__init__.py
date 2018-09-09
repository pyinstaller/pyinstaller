#-----------------------------------------------------------------------------
# Copyright (c) 2013-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


""" pkg2 does various namespace tricks, __path__ append """

def notamodule():
    return "notamodule from pkg2.__init__"

import os
__path__.append(os.path.join(
    os.path.dirname(__file__), 'extra'))
__all__ = ["a", "b", "notamodule"]
