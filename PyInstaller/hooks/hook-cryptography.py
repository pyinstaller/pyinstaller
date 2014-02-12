"""
Hook for cryptography module from the Python Cryptography Authority.
"""
import os.path
import glob
from functools import partial
from operator import concat
from cryptography.hazmat.bindings.openssl.binding import Binding as _SSLBinding

# add the FFI bindings' modules as hidden imports
hiddenimports = map(partial(concat, _SSLBinding._module_prefix), _SSLBinding._modules)


# include the cffi extensions as binaries
def hook(mod):
    cryptography_dir = os.path.dirname(mod.__file__)
    for ext in ('pyd', 'so'):
        ffimods = glob.glob(os.path.join(cryptography_dir, '_cffi_*.%s*' % ext))
        for f in ffimods:
            name = os.path.join('cryptography', os.path.basename(f))
            mod.binaries.append((name, f, 'BINARY'))
    return mod
