import basemod

DATA_FROM_RTHOOK = "This is data from the RT-Hook"

class _Popen(basemod.Popen):
    def __init__(self, *args, **kw):
        super(_Popen, self).__init__(*args, **kw)

basemod.Popen = _Popen
