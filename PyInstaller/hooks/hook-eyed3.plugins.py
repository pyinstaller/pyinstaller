from PyInstaller.utils.hooks import collect_data_files, collect_submodules
from os.path import basename, splitext

plugins = filter(lambda data: basename(data[0])[0] not in ('_', '.') and data[0].endswith('.py'),
        collect_data_files('eyed3.plugins', include_py_files=True))

datas = plugins

imports = list(set(map(lambda data: splitext(basename(data[0]))[0],
        datas)))

hiddenimports = imports
