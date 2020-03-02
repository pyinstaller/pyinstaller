
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

hiddenimports = collect_submodules('pysnmp_mibs')
datas = collect_data_files('pysnmp_mibs', include_py_files=True)
