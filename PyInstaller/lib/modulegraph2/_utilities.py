"""
Some useful utility functions.
"""
import contextlib
import importlib
import sys
from typing import List, Optional, Tuple


@contextlib.contextmanager
def saved_sys_path():
    """
    Contextmanager that will restore the value
    of :data:`sys.path` when leaving the ``with``
    block.
    """
    orig_path = list(sys.path)

    try:
        yield

    finally:
        sys.path[:] = orig_path
        importlib.invalidate_caches()


def split_package(name: str) -> Tuple[Optional[str], str]:
    """
    Return (package, name) given a fully qualified module name

    package is ``None`` for toplevel modules
    """
    if not isinstance(name, str):
        raise TypeError(f"Expected 'str', got instance of {type(name)!r}")
    if not name:
        raise ValueError(f"Invalid module name {name!r}")

    name_abs = name.lstrip(".")
    dots = len(name) - len(name_abs)
    if not name_abs or ".." in name_abs:
        raise ValueError(f"Invalid module name {name!r}")

    package, _, name = name_abs.rpartition(".")
    if dots:
        package = ("." * dots) + package

    return (package if package != "" else None), name


class FakePackage:
    """
    Instances of these can be used to represent a fake
    package in :data:`sys.modules`.

    Used as a workaround to fetch information about modules
    in packages when the package itself cannot be imported
    for some reason (for example due to having a SyntaxError
    in the module ``__init__.py`` file).
    """

    def __init__(self, path: List[str]):
        """
        Create a new instance.

        Args:
           path: The search path for sub modules
        """
        self.__path__ = path
