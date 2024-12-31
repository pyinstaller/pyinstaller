from PyInstaller.utils.hooks import collect_submodules, collect_data_files

hiddenimports = collect_submodules('pyi_test_nspkg')
datas = collect_data_files('pyi_test_nspkg')
