"""
pyopencl: https://mathema.tician.de/software/pyopencl/
"""

from PyInstaller.utils.hooks import copy_metadata, collect_data_files
datas = copy_metadata('pyopencl')
datas += collect_data_files('pyopencl')
