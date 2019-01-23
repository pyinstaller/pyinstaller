"""
Support for PyPI packages

Note: This assumes that the contents of distributions don't change
during a run of the script.
"""
import os
import sys
from email.parser import BytesParser
from importlib.machinery import EXTENSION_SUFFIXES
from typing import Dict, Iterable, Iterator, List, Optional, Set, Union

import dataclasses


@dataclasses.dataclass(frozen=True)
class PyPIDistribution:
    """
    Information about a python package distribution
    """

    identifier: str  # "Random" identifier, not a valid python module name
    name: str  # Name of the distribution
    version: str  # Version of the distribution
    files: Set[str]  # List of files in the distribution, as absolute paths
    import_names: Set[str]  # List of importable names in this distribution

    def contains_file(self, filename: Union[str, os.PathLike]):
        return os.fspath(filename) in self.files


def create_distribution(distribution_file: str) -> PyPIDistribution:
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


def all_distributions(path: Iterable[str] = sys.path) -> Iterator[PyPIDistribution]:
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
    filename: Union[str, os.PathLike], path: Iterable[str]
) -> Optional[PyPIDistribution]:
    """
    Find a distribution for a given file, for installed distributions.

    Raises FileNotFoundError when no distribution can be found
    """
    for dist in all_distributions(path):
        if dist.contains_file(filename):
            return dist

    return None


def distribution_named(
    name: str, path: Iterable[str] = sys.path
) -> Optional[PyPIDistribution]:
    for dist in all_distributions(path):
        if dist.name == name:
            return dist

    return None
