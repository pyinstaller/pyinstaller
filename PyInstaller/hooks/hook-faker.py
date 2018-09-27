from PyInstaller.utils.hooks import collect_submodules, collect_data_files
hiddenimports = collect_submodules('faker')
datas = collect_data_files('faker', include_py_files=True)
