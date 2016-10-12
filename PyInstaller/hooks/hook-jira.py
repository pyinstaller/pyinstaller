from PyInstaller.utils.hooks import copy_metadata, collect_submodules

datas = copy_metadata('jira')
hiddenimports = collect_submodules('jira')
