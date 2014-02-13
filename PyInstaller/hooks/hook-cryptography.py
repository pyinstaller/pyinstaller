"""
Hook for cryptography module from the Python Cryptography Authority.
"""
import os.path
import glob
from hookutils import collect_submodules

# add the OpenSSL FFI binding modules as hidden imports
hiddenimports = collect_submodules('cryptography.hazmat.bindings.openssl')

# include the cffi extensions as binaries
def hook(mod):
    cryptography_dir = os.path.dirname(mod.__file__)
    for ext in ('pyd', 'so'):
        ffimods = glob.glob(os.path.join(cryptography_dir, '_cffi_*.%s*' % ext))
        for f in ffimods:
            name = os.path.join('cryptography', os.path.basename(f))
            mod.pyinstaller_binaries.append((name, f, 'BINARY'))
    return mod
