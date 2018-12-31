"""
Helpers for implied imports

NOTE:
- This is based on manual inspection
  of the stdlib sources...
"""


import sys
import os


class Alias(str):
    pass


STDLIB_IMPLIES = {
    #
    # C extensions
    #
    "_asyncio": (
        "asyncio",
        "asyncio.events",
        "asyncio.base_futures",
        "asyncio.base_tasks",
        "asyncio.coroutines",
        "inspect",
        "traceback",
        "weakref",
    ),
    "_curses": ("curses",),
    "_datetime": ("time", "_strptime"),
    "_elementtree": ("copy", "xml.etree.ElementPath", "pyexpat"),
    "_json": ("json.decoder",),
    "_operator": ("functools",),
    "_pickle": ("copyreg", "_compat_pickle", "codecs", "functools"),
    "_posixsubprocess": ("gc",),
    "_ssl": ("_socket",),
    "_overlapped": ("_socket",),
    "parser": ("copyreg",),
    "posix": ("resource",),
    "signal": ("_signal",),
    "time": ("_strptime",),
    "zipimport": ("importlib.resources", "zlib"),
    #
    # Python module
    #
    "os.path": Alias(os.path.__name__),
    "sysconfig": "_sysconfigdata_{abi}_{platform}_{multiarch}".format(
        abi=sys.abiflags,
        platform=sys.platform,
        multiarch=getattr(sys.implementation, "_multiarch", ""),
    ),
    "turtledemo": (
        "turtledemo.colormixer",
        "turtledemo.nim",
        "turtledemo.rosette",
        "turtledemo.yinyang",
        "turtledemo.forest",
        "turtledemo.paint",
        "turtledemo.round_dance",
        "turtledemo.bytedesign",
        "turtledemo.fractalcurves",
        "turtledemo.peace",
        "turtledemo.sorting_animate",
        "turtledemo.chaos",
        "turtledemo.lindenmayer",
        "turtledemo.penrose",
        "turtledemo.tree",
        "turtledemo.clock",
        "turtledemo.minimal_hanoi",
        "turtledemo.planet_and_moon",
        "turtledemo.two_canvases",
    ),
    "dbm": ("dbm.gnu", "dbm.ndbm", "dbm.dumb"),
}

if sys.platform == "win32":
    STDLIB_IMPLIES["signal"] = STDLIB_IMPLIES["signal"] + ("_socket",)
    STDLIB_IMPLIES["ctypes"] = ("comtypes.server.inprocserver",)
