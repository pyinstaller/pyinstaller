import os

from PyInstaller.utils.hooks import get_package_paths
from PyInstaller import compat

if compat.is_win:
    binaries = []
    pkb_base, pkg_dir = get_package_paths('shapely')
    lib_dir = os.path.join(pkg_dir, 'DLLs')
    binaries += [(os.path.join(lib_dir, f), '') for f in os.listdir(lib_dir)]
