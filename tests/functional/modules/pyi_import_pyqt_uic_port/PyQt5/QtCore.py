# fake module to make PyQt5 hooks and run-time-hooks happy
__pyinstaller_fake_module_marker__ = '__pyinstaller_fake_module_marker__'


class QLibraryInfo:
    def __init__(*args, **kw):
        pass

    PrefixPath = 1
    BinariesPath = 2

    @classmethod
    def location(cls, val):
        return "."

    @classmethod
    def isDebugBuild(cls):
        return False
