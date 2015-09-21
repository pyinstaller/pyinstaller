from PyInstaller.utils.hooks import get_typelibs

hiddenimports = ['gi.overrides.GLib']

datas = get_typelibs('GLib', '2.0')
