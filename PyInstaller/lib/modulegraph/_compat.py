import sys

if sys.version_info[0] == 2:
    PY2 = True

    from StringIO import StringIO
    BytesIO = StringIO
    from urllib import pathname2url
    _cOrd = ord

    # File open mode for reading (univeral newlines)
    _READ_MODE = "rU"

    def Bchr(value):
        return chr(value)

else:
    PY2 = False

    from urllib.request import pathname2url
    from io import BytesIO, StringIO
    _cOrd = int
    _READ_MODE = "r"

    def Bchr(value):
        return value

if sys.version_info < (3,):
    from dis3 import get_instructions
elif sys.version_info < (3, 4):
    from xdis.std import get_instructions
else:
    from dis import get_instructions
