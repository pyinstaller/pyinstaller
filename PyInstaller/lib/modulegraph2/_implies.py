"""
Helpers for implied imports

NOTE:
- This is based on manual inspection
  of the stdlib sources...
"""


import os
import sys
from typing import Dict, Sequence, Union


class Alias(str):
    pass


ImpliesValueType = Union[None, Alias, Sequence[str]]


STDLIB_IMPLIES: Dict[str, ImpliesValueType] = {
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
    # typing.io is "just" a namespace created by "typing", not a
    # real module.
    "typing.io": Alias("typing"),
    "typing.re": Alias("typing"),
    # os.path is a virtual package
    "os.path": Alias(os.path.__name__),
    # sysconfig users __import__ to load platform specific data
    "sysconfig": (
        "_sysconfigdata_{abi}_{platform}_{multiarch}".format(
            abi=sys.abiflags,
            platform=sys.platform,
            multiarch=getattr(sys.implementation, "_multiarch", ""),
        ),
    ),
    # turtledemo uses __import__ to load the actual demos
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
    # Uses __import__
    "dbm": ("dbm.gnu", "dbm.ndbm", "dbm.dumb"),
}

STDLIB_PLATFORM_IMPLIES: Dict[str, Dict[str, ImpliesValueType]] = {
    "win32": {
        "signal": ("_signal", "_socket"),
        "ctypes": ("comtypes.server.inprocserver",),
    }
}

STDLIB_IMPLIES.update(STDLIB_PLATFORM_IMPLIES.get(sys.platform, {}))

if sys.version_info[:2] < (3, 7):
    # The earlier definition includes a module
    # introduced in 3.7
    STDLIB_IMPLIES["zipimport"] = ("zlib",)
