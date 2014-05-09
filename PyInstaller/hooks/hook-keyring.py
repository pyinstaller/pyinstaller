from PyInstaller.hooks.hookutils import collect_submodules

hiddenimports = collect_submodules('keyring.backends')
