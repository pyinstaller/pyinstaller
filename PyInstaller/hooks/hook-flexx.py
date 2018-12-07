import os
from PyInstaller.utils.hooks import collect_data_files, get_module_file_attribute

datas = collect_data_files('flexx', include_py_files=True)

# We must also collect flexx source code manually and add it to data to
# allow transpilation of py->js.
flexx_py_path = os.path.dirname(get_module_file_attribute('flexx'))

datas = datas + [
    (flexx_py_path, 'flexx'),
    (flexx_py_path, 'site-packages/flexx'),
]
