#-----------------------------------------------------------------------------
# Copyright (c) 2005-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

"""
Hook for PyCryptodome library: https://pypi.python.org/pypi/pycryptodome

PyCryptodome is an almost drop-in replacement for the now unmaintained
PyCrypto library. The two are mutually exclusive as they live under
the same package ("Crypto").

Even though this hook is meant to help with PyCryptodome only, it will be
triggered also when PyCrypto is installed, so it must be tested with both.

Tested with PyCryptodome 3.5.1, PyCrypto 2.6.1, Python 2.7 & 3.6, Fedora & Windows
"""

import os
import glob

from PyInstaller.compat import EXTENSION_SUFFIXES
from PyInstaller.utils.hooks import get_module_file_attribute

# Include the modules as binaries in a subfolder named like the package.
# Cryptodome's loader expects to find them inside the package directory for
# the main module. We cannot use hiddenimports because that would add the
# modules outside the package.

binaries = []
binary_module_names = [
    'Crypto.Cipher',
    'Crypto.Util',
    'Crypto.Hash',
    'Crypto.Protocol',
    'Crypto.Math',
]

for module_name in binary_module_names:
    try:
        m_dir = os.path.dirname(get_module_file_attribute(module_name))
    except ImportError:
        continue
    for ext in EXTENSION_SUFFIXES:
        module_bin = glob.glob(os.path.join(m_dir, '_*%s' % ext))
        for f in module_bin:
            binaries.append((f, module_name.replace('.', '/')))
