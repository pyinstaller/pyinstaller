#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


try:
    import excluded_module
    raise SystemExit('Excluded module was not excluded.')
except ImportError:
    pass  # the test is successful.
