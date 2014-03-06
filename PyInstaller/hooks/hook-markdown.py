from PyInstaller.hooks.hookutils import collect_submodules, collect_data_files

hiddenimports = collect_submodules('markdown.extensions')
