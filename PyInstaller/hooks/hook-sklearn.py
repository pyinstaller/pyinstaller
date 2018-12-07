from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files('sklearn')
hiddenimports = ['sklearn.neighbors.typedefs']
