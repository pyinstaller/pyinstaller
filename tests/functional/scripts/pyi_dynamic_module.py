#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import pyi_testmod_dynamic


if __name__ == "__main__":
    # The value 'foo' should  not be None.
    print("'foo' value: %s" % pyi_testmod_dynamic.foo)
    assert pyi_testmod_dynamic.foo is not None
    assert pyi_testmod_dynamic.foo == 'A new value!'
