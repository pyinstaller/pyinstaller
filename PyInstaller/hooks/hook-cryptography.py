#-----------------------------------------------------------------------------
# Copyright (c) 2014, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Hook for cryptography module from the Python Cryptography Authority.
"""

import os.path
import glob
from hookutils import collect_submodules, get_module_file_attribute

# add the OpenSSL FFI binding modules as hidden imports
hiddenimports = collect_submodules('cryptography.hazmat.bindings.openssl')

def hook(mod):
    cryptography_dir = os.path.dirname(get_module_file_attribute('cryptography'))
    for ext in ('pyd', 'so'):
        ffimods = glob.glob(os.path.join(cryptography_dir, '_cffi_*.%s*' % ext))
        for f in ffimods:
            name = os.path.join('cryptography', os.path.basename(f))
            mod.pyinstaller_binaries.append((name, f, 'BINARY'))
    return mod
