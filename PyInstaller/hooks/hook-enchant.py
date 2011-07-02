import sys

if sys.platform == 'win32':
    from PyInstaller.hooks.hookutils import enchant_win32_data_files
    datas = enchant_win32_data_files()
