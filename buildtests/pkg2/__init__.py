""" pkg2 does various namespace tricks, __path__ append """

def notamodule():
    return "notamodule from pkg2.__init__"

import os
__path__.append(os.path.join(
    os.path.dirname(__file__), 'extra'))
__all__ = ["a", "b", "notamodule"]
