from PyInstaller.utils.hooks import get_typelibs

hiddenimports = ['gi.overrides.GModule']

datas = get_typelibs('GModule', '2.0')
