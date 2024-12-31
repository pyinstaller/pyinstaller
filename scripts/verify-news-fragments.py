#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Copyright (c) 2013-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""
Verify that new news entries have valid filenames. Usage:

.. code-block:: bash

    ./scripts/verify-news-fragments.py

"""

import re
import sys
from pathlib import Path

CHANGELOG_GUIDE = (
    "https://github.com/pyinstaller/pyinstaller/"
    "blob/develop/doc/development/changelog-entries.rst#changelog-entries"
)

CHANGE_TYPES = {
    'bootloader', 'breaking', 'bugfix', 'build', 'core', 'doc', 'feature', 'hooks', 'moduleloader', 'process', 'tests',
    'deprecation'
}

NEWS_PATTERN = re.compile(r"(\d+)\.(\w+)\.(?:(\d+)\.)?rst")

NEWS_DIR = Path(__file__).absolute().parent.parent / "news"


def validate_name(name):
    """
    Check a filename/filepath matches the required format.

    :param name: Name of news fragment file.
    :type: str, os.Pathlike

    :raises: ``SystemExit`` if above checks don't pass.
    """
    match = NEWS_PATTERN.fullmatch(Path(name).name)
    if match is None:
        raise SystemExit(
            f"'{name}' does not match the '(pr-number).(type).rst' or '(pr-number).(type).(enumeration).rst' changelog "
            f"entries formats. See:\n{CHANGELOG_GUIDE}"
        )

    if match.group(2) not in CHANGE_TYPES:
        sys.exit("'{}' of of invalid type '{}'. Valid types are:\n{}".format(name, match.group(2), CHANGE_TYPES))

    print(name, "is ok")


def main():
    for file in NEWS_DIR.iterdir():
        if file.name in ["README.txt", "_template.rst", ".gitignore"]:
            continue
        validate_name(file)


if __name__ == "__main__":
    main()
