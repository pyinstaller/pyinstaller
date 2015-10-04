#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


try:
    import pyimod00_crypto_key

    raise AssertionError('The pyimod00_crypto_key module must NOT be there if crypto is disabled.')
except ImportError:
    pass
