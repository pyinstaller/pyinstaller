# fake module to make PyQt5 hooks and run-time-hooks happy
__pyinstaller_fake_module_marker__ = '__pyinstaller_fake_module_marker__'

class QCoreApplication:
    def __init__(*args, **kw): pass

    @classmethod
    def setLibraryPaths(*args, **kw): pass

    def libraryPaths(*args, **kw): return []

# required to make hook-PyQt5 happy
QT_VERSION_STR = '99.99.99'
