#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Copyright (c) 2013-2020, PyInstaller Development Team.
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

    git diff --name-status $COMMIT_ID | python verify-news-fragments.py

If you have a Pull Request number then you can verify that new entries have
the correct PR number in their filename:

.. code-block:: bash

    git diff --name-status origin/${{ github.base_ref }} \
    | python verify-news-fragments.py $PR_NUMBER

"""

import re
import sys
from pathlib import Path

CHANGELOG_GUIDE = (
    "https://github.com/pyinstaller/pyinstaller/"
    "blob/develop/doc/development/changelog-entries.rst#changelog-entries")

CHANGE_TYPES = {'bootloader', 'break', 'bugfix', 'build', 'core', 'doc',
                'feature', 'hooks', 'moduleloader', 'process', 'tests'}

NEWS_PATTERN = re.compile(r"(\d+)\.(\w+)\.rst")

NEWS_DIR = Path(__file__).absolute().parent.parent / "news"


def validate_name(name, pr_num=None):
    """Check a filename/filepath matches the required format.
    If **pr** is provided, also check that the filename has the
    correct PR number.

    Raises ValueError
    :param name: Name of news fragment file.
    :type: str, os.Pathlike

    :param pr_num: Pull request number to validate.
    :type pr_num: int, str, optional

    :raises: ``SystemExit`` if above checks don't pass.
    """
    match = NEWS_PATTERN.fullmatch(Path(name).name)
    if match is None:
        sys.exit("'{}' does not match '(pr-number).(type).rst' changelog"
                 "entries format. See:\n{}".format(name, CHANGELOG_GUIDE))

    if match.group(2) not in CHANGE_TYPES:
        sys.exit("'{}' of of invalid type '{}'. Valid types are:\n{}".format(
            name, match.group(2), CHANGE_TYPES))

    if (pr_num is not None) and (int(pr_num) != int(match.group(1))):
        sys.exit("'{}' has pull request number {} but the pull request "
                 "is actually #{}.".format(name, match.group(1), pr_num))

    print(name, "is ok")


def main(pr=None):
    # Parse the output of `git diff --name-status COMMIT`
    lines = sys.stdin.readlines()

    for line in lines:
        try:
            action, filename = line.split(maxsplit=1)
        except ValueError:
            continue
        filename = Path(filename.strip())

        if action == "A" and filename.parts[0] == "news":
            if filename.suffix == ".rst":
                validate_name(filename, pr)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) == 2 else None)
