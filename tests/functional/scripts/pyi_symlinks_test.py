#-----------------------------------------------------------------------------
# Copyright (c) 2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import os
import sys
import argparse

SECRET = 'secret'

# Argument parser
parser = argparse.ArgumentParser(description="symbolic link collection test")
parser.add_argument(
    'test_type',
    type=str,
    help='Test type',
    choices=['samedir', 'subdir', 'parentdir'],
)
parser.add_argument(
    '--link-only',
    action='store_true',
    dest='link_only',
    default=False,
    help="Symlink-only test variant.",
)
args = parser.parse_args()

# Data dir
data_dir = os.path.join(sys._MEIPASS, 'data')

# Test modes / parametrization
if args.test_type == 'samedir':
    orig_file = None if args.link_only else os.path.join(data_dir, 'orig_file.txt')
    linked_file = os.path.join(data_dir, 'linked_file.txt')
elif args.test_type == 'subdir':
    orig_file = None if args.link_only else os.path.join(data_dir, 'subdir', 'orig_file.txt')
    linked_file = os.path.join(data_dir, 'linked_file.txt')
elif args.test_type == 'parentdir':
    orig_file = None if args.link_only else os.path.join(data_dir, 'orig_file.txt')
    linked_file = os.path.join(data_dir, 'subdir', 'linked_file.txt')

# Validation
if orig_file:
    # Check original file - must be a valid file and must not be a symbolic link
    print(f"Checking original file {orig_file}...", file=sys.stderr)
    assert os.path.isfile(orig_file), f"{orig_file} is not a file!"
    assert not os.path.islink(orig_file), f"{orig_file} is a symbolic link?!"
    with open(orig_file, 'r') as fp:
        assert fp.read() == SECRET, f"Invalid content in {orig_file}!"

    # Check linked file - must be a valid file (pointing to one) and must be a symbolic link
    print(f"Checking linked file {linked_file}...", file=sys.stderr)
    assert os.path.isfile(linked_file), f"{linked_file} is not a file!"
    assert os.path.islink(linked_file), f"{linked_file} is not a symlink!"
    with open(linked_file, 'r') as fp:
        assert fp.read() == SECRET, f"Invalid content in {linked_file}!"
else:
    # Check linked file - must be a valid file (pointing to one) and must NOT be a symbolic link (because original was
    # not collected)
    print(f"Checking only linked file {linked_file}...", file=sys.stderr)
    assert os.path.isfile(linked_file), f"{linked_file} is not a file!"
    assert not os.path.islink(linked_file), f"{linked_file} is a symbolic link, but it should not be!"
    with open(linked_file, 'r') as fp:
        assert fp.read() == SECRET, f"Invalid content in {linked_file}!"
