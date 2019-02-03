"""
Definitions related to implied imports.

The implies in this file are based on manual
inspection of the stdlib sources for CPython.
"""


import os
import sys
from typing import Dict, Sequence, Tuple, Union


class Alias(str):
    """
    Alias for a module name

    Aliases are used in "implies" configuration to specify
    that a module name is actually an alias for some other
    name. An instance of this class is used to represent.
    the name of the other module.
    """

    __slots__ = ()


class Virtual(str):
    """
    Virtual package provided by a module

    Virtuals are used in "implies" configuration to specify
    that a module name is actually the name of a virtual
    module provided by another module.  An instance of
    this class is used to represent the name of the
    other module.
    """

    __slots__ = ()


#: The type for the value in an implies dictionary.
ImpliesValueType = Union[None, Alias, Virtual, Sequence[str]]


#: Implies dictionary for the standard library.
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
    "typing.io": Virtual("typing"),
    "typing.re": Virtual("typing"),
    # os.path is a virtual package
    "os.path": Alias(os.path.__name__),
    # sysconfig users __import__ to load platform specific data
    "sysconfig": (
        "_sysconfigdata_{abi}_{platform}_{multiarch}".format(
            abi=getattr(sys, "abiflags", ""),
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

#: Updates to the base :data:`STDLIB_IMPLIES` for specific platforms.
STDLIB_PLATFORM_IMPLIES: Dict[str, Dict[str, ImpliesValueType]] = {
    "win32": {
        "signal": ("_signal", "_socket"),
        "ctypes": ("comtypes.server.inprocserver",),
        "sysconfig": (),
        "posix": (),
    }
}

STDLIB_IMPLIES.update(STDLIB_PLATFORM_IMPLIES.get(sys.platform, {}))


#: Updates to the base :data:`STDLIB_IMPLIES` for specific Python releases.
STDLIB_VERSION_IMPLIES: Dict[Tuple[int, int], Dict[str, ImpliesValueType]] = {
    (3, 6): {
        "zipimport": ("zlib",),
        "turtledemo": (
            "turtledemo.chaos",
            "turtledemo.fractalcurves",
            "turtledemo.paint",
            "turtledemo.round_dance",
            "turtledemo.two_canvases",
            "turtledemo.clock",
            "turtledemo.lindenmayer",
            "turtledemo.peace",
            "turtledemo.sorting_animate",
            "turtledemo.wikipedia",
            "turtledemo.colormixer",
            "turtledemo.minimal_hanoi",
            "turtledemo.penrose",
            "turtledemo.tree",
            "turtledemo.yinyang",
            "turtledemo.bytedesign",
            "turtledemo.forest",
            "turtledemo.nim",
            "turtledemo.planet_and_moon",
        ),
    }
}

STDLIB_IMPLIES.update(STDLIB_VERSION_IMPLIES.get(sys.version_info[:2], {}))
