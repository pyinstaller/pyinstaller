import os
from PyInstaller.utils.hooks import get_package_paths

datas = []
_, mip_path = get_package_paths("mip")
lib_path = os.path.join(mip_path, "libraries")

for f in os.listdir(lib_path):
    if f.endswith(".so") or f.endswith(".dll") or f.endswith(".dylib"):
        datas.append((os.path.join(lib_path, f), "mip/libraries"))
