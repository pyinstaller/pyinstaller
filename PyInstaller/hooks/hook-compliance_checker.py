from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all('compliance_checker', include_py_files=True)
