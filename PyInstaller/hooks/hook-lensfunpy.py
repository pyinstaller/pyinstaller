from hookutils import collect_data_files
# bundle xml DB files, skip other files (like DLL files on Windows)
datas = list(filter(lambda p: p[0].endswith('.xml'), collect_data_files('lensfunpy')))
hiddenimports = ['numpy', 'enum']
