#-----------------------------------------------------------------------------
# Copyright (c) 2014, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import imp


try:
    imp.find_module('pyi_crypto')

    raise AssertionError('The pyi_crypto module must NOT be there if crypto is disabled.')
except ImportError:
    pass


try:
    imp.find_module('pyi_crypto_key')

    raise AssertionError('The pyi_crypto_key module must NOT be there if crypto is disabled.')
except ImportError:
    pass
