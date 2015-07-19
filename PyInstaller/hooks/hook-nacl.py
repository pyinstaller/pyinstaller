import os.path
import glob
from PyInstaller.hooks.hookutils import collect_data_files, get_module_file_attribute

datas = collect_data_files('nacl')

def hook(mod):
    """
    Include the cffi extensions as binaries in a subfolder named like the package.
    """
    nacl_dir = os.path.dirname(get_module_file_attribute('nacl'))
    ffimods = glob.glob(os.path.join(nacl_dir, '_lib', '*_cffi_*.so'))
    for f in ffimods:
        name = os.path.join('nacl', '_lib', os.path.basename(f))
        mod.binaries.append((name, f, 'BINARY'))
    return mod
