"""
This module contains functions and classes that are used
to process information about package distributions (the
stuff on PyPI).
"""
import dataclasses
import os
import sys
from email.parser import BytesParser
from importlib.machinery import EXTENSION_SUFFIXES
from typing import Dict, Iterable, Iterator, List, Optional, Set, Union


@dataclasses.dataclass(frozen=True)
class PyPIDistribution:
    """
    Information about a package distribution

    Attributes:
      identifier (str):  Unique identifier fot the distribution for use with
                   :class:`modulegraph2.ObjectGraph`

      name (str): Name of the distribution (as it is found on PyPI)

      files (Set[str]): Files that are part of this distribution

      import_names (Set[str]): The importable names in this distribution
                   (modules and packages)

    .. note::

       The information about distributions is fairly minimal at this point,
       and will be enhanced as needed.
    """

    identifier: str
    name: str
    version: str
    files: Set[str]
    import_names: Set[str]

    def contains_file(self, filename: Union[str, os.PathLike]):
        """
        Check if a file is part of this distribution.

        Args:
           filename: The filename to look for

        Returns:
           True if *filename* is part of this distribution, otherwise False.
        """
        return os.fspath(filename) in self.files


def create_distribution(distribution_file: str) -> PyPIDistribution:
    """
    Create a distribution object for a given dist-info directory.

    Args:
      distribution_file: Filename for a dist-info directory

    Returns
      A :class:`PyPIDistribution` for *distribution_file*
    """
    files: List[str] = []
    import_names: List[str] = []

    distribution_dir = os.path.dirname(distribution_file)

    with open(os.path.join(distribution_file, "METADATA"), "rb") as meta_fp:
        info = BytesParser().parse(meta_fp)

    name = info["Name"]
    assert isinstance(name, str)
    version = info["Version"]
    assert isinstance(version, str)

    with open(os.path.join(distribution_file, "RECORD")) as record_fp:
        all_suffixes = [".py", ".pyc"] + EXTENSION_SUFFIXES

        for ln in record_fp:
            # The RECORD file is a CSV file according to PEP 376, but
            # the wheel spec is silent on this and the wheel tool
            # creates files that aren't necessarily correct CSV files
            # (See issue #280 at https://github.com/pypa/wheel)
            #
            # This code works for all filenames, except those containing
            # line seperators.
            relpath = ln.rsplit(",", 2)[0]

            if relpath.startswith('"') and relpath.endswith('"'):
                # The record file is a CSV file that can contain quoted strings.
                relpath = relpath[1:-1].replace('""', '"')

            abspath = os.path.normpath(os.path.join(distribution_dir, relpath))
            files.append(abspath)

            if "/__pycache__/" in relpath or relpath.startswith("__pycache__/"):
                continue

            for suffix in all_suffixes:
                if not relpath.endswith(suffix):
                    continue

                if relpath.endswith("/__init__" + suffix):
                    import_names.append(
                        relpath[: -len("/__init__") + -len(suffix)].replace("/", ".")
                    )

                else:
                    import_names.append(relpath[: -len(suffix)].replace("/", "."))

                break

    return PyPIDistribution(
        distribution_file, name, version, set(files), set(import_names)
    )


_cached_distributions: Dict[str, PyPIDistribution] = {}


def all_distributions(
    path: Optional[Iterable[str]] = None,
) -> Iterator[PyPIDistribution]:
    """
    Yield all distributions found on the search path.

    Args:
       path: Module search path (defaults to :data:`sys.path`).
    """
    if path is None:
        path = sys.path

    for entry in path:
        try:
            for fname in os.listdir(entry):
                if not fname.endswith(".dist-info"):
                    continue

                dist_name = os.path.join(entry, fname)

                try:
                    dist = _cached_distributions[dist_name]

                except KeyError:
                    dist = create_distribution(dist_name)
                    _cached_distributions[dist_name] = dist

                yield dist

        except os.error:
            continue


def distribution_for_file(
    filename: Union[str, os.PathLike], path: Optional[Iterable[str]]
) -> Optional[PyPIDistribution]:
    """
    Find a distribution for a given file, for installed distributions.

    Args:
      filename: Filename to look for
      path: Module search path (defaults to :data:`sys.path`)

    Returns:
      The distribution that contains *filename*, or None
    """
    for dist in all_distributions(path):
        if dist.contains_file(filename):
            return dist

    return None


def distribution_named(
    name: str, path: Optional[Iterable[str]] = None
) -> Optional[PyPIDistribution]:
    """
    Find a named distribution on the search path.

    Args:
      name: Distribution name to look for.
      path: Module search path (defaults to :data:`sys.path`)

    Returns:
      The distribution, or None
    """
    for dist in all_distributions(path):
        if dist.name == name:
            return dist

    return None
