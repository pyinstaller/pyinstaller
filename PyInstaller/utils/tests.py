#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------



"""
Decorators for skipping PyInstaller tests when specific requirements are not met.
"""

import pytest
from PyInstaller.compat import is_darwin, is_win

# Wrap some pytest decorators to be consistent in tests.
skipif = pytest.mark.skipif
skipif_notwin = skipif(not is_win, reason='requires Windows')
skipif_notosx = skipif(not is_darwin, reason='requires Mac OS X')
skipif_winorosx = skipif(is_win or is_darwin, reason='does not run on Windows or Mac OS X')

xfail = pytest.mark.xfail


def importorskip(modules):
    """
    This wraps the pytest decorator to evaluate all modules that are required
    for running a test.

    :param modules: Module name or list of modules.
    :return: pytest decorator with a reason and list of required modules.
    """
    mods_avail = True
    # Convert string to a list with one item.
    if type(modules) is str:
        modules = [modules]
    for m in modules:
        try:
            __import__(m)
        except ImportError:
            mods_avail = False
    # Return pytest decorator.
    return skipif(not mods_avail, reason='requires modules %s' % ', '.join(modules))
