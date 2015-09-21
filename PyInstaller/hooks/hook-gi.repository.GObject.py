from PyInstaller.utils.hooks import get_typelibs

hiddenimports = ['gi.overrides.GObject', 'gi._gobject.option', 'gi._gobject']

datas = get_typelibs('GObject', '2.0')
