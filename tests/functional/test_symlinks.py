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

import pytest

from PyInstaller.compat import is_win


def _create_data(tmpdir, orig_filename, link_filename):
    # Create data directory
    data_path = os.path.join(tmpdir, "data")

    # Create original file
    abs_orig_filename = os.path.join(data_path, orig_filename)
    os.makedirs(os.path.dirname(abs_orig_filename), exist_ok=True)
    with open(abs_orig_filename, 'w') as fp:
        fp.write("secret")

    # Create symbolic link
    abs_linked_filename = os.path.join(data_path, link_filename)
    os.makedirs(os.path.dirname(abs_linked_filename), exist_ok=True)
    rel_orig_filename = os.path.relpath(abs_orig_filename, os.path.dirname(abs_linked_filename))

    try:
        os.symlink(rel_orig_filename, abs_linked_filename)
    except OSError:
        if is_win:
            pytest.skip("OS does not support creation of symbolic links.")
        else:
            raise


# Collect both symbolic link and file
def test_symlinks__samedir__symlink_and_file(tmpdir, script_dir, pyi_builder):
    # Create test data
    _create_data(tmpdir, 'orig_file.txt', 'linked_file.txt')

    # Collect both original file and symbolic link
    data_dir = os.path.join(tmpdir, 'data')
    add_data_args = [
        '--add-data', os.path.join(data_dir, 'orig_file.txt') + os.pathsep + 'data',
        '--add-data', os.path.join(data_dir, 'linked_file.txt') + os.pathsep + 'data',
    ]  # yapf: disable

    # Run test script in 'samedir' mode
    pyi_builder.test_script(
        os.path.join(str(script_dir), 'pyi_symlinks_test.py'),
        pyi_args=add_data_args,
        app_args=['samedir'],
    )


# Same as test_symlinks__samedir__symlink_and_file, except that we collect whole data directory instead of
# individual files.
def test_symlinks__samedir__wholedir(tmpdir, script_dir, pyi_builder):
    # Create test data
    _create_data(tmpdir, 'orig_file.txt', 'linked_file.txt')

    # Collect whole data directory
    data_dir = os.path.join(tmpdir, 'data')
    add_data_args = [
        '--add-data', data_dir + os.pathsep + 'data',
    ]  # yapf: disable

    # Run test script in 'samedir' mode
    pyi_builder.test_script(
        os.path.join(str(script_dir), 'pyi_symlinks_test.py'),
        pyi_args=add_data_args,
        app_args=['samedir'],
    )


# Collect only symbolic link
def test_symlinks__samedir__symlink_only(tmpdir, script_dir, pyi_builder):
    # Create test data
    _create_data(tmpdir, 'orig_file.txt', 'linked_file.txt')

    # Collect only symbolic link
    data_dir = os.path.join(tmpdir, 'data')
    add_data_args = [
        '--add-data', os.path.join(data_dir, 'linked_file.txt') + os.pathsep + 'data',
    ]  # yapf: disable

    # Run test script in 'samedir/link-only' mode
    pyi_builder.test_script(
        os.path.join(str(script_dir), 'pyi_symlinks_test.py'),
        pyi_args=add_data_args,
        app_args=['samedir', '--link-only'],
    )


# Collect symbolic link and original file, but place the latter somewhere else
def test_symlinks__samedir__orig_elsewhere(tmpdir, script_dir, pyi_builder):
    # Create test data
    _create_data(tmpdir, 'orig_file.txt', 'linked_file.txt')

    # Collect only symbolic link
    data_dir = os.path.join(tmpdir, 'data')
    add_data_args = [
        '--add-data', os.path.join(data_dir, 'orig_file.txt') + os.pathsep + 'data2',
        '--add-data', os.path.join(data_dir, 'linked_file.txt') + os.pathsep + 'data',
    ]  # yapf: disable

    # Run test script in 'samedir/link-only' mode (this should effectively be the same as 'link-only' scenario)
    pyi_builder.test_script(
        os.path.join(str(script_dir), 'pyi_symlinks_test.py'),
        pyi_args=add_data_args,
        app_args=['samedir', '--link-only'],
    )


# Test symbolic link pointing to a subdirectory
def test_symlinks__subdir__wholedir(tmpdir, script_dir, pyi_builder):
    # Create test data
    _create_data(tmpdir, os.path.join('subdir', 'orig_file.txt'), 'linked_file.txt')

    # Collect whole data directory
    data_dir = os.path.join(tmpdir, 'data')
    add_data_args = [
        '--add-data', data_dir + os.pathsep + 'data',
    ]  # yapf: disable

    # Run test script in 'subdir' mode
    pyi_builder.test_script(
        os.path.join(str(script_dir), 'pyi_symlinks_test.py'),
        pyi_args=add_data_args,
        app_args=['subdir'],
    )


# Test symbolic link pointing to a subdirectory - symlink only
def test_symlinks__subdir__symlink_only(tmpdir, script_dir, pyi_builder):
    # Create test data
    _create_data(tmpdir, os.path.join('subdir', 'orig_file.txt'), 'linked_file.txt')

    # Collect only symbolic link
    data_dir = os.path.join(tmpdir, 'data')
    add_data_args = [
        '--add-data', os.path.join(data_dir, 'linked_file.txt') + os.pathsep + 'data',
    ]  # yapf: disable

    # Run test script in 'subdir/link-only' mode
    pyi_builder.test_script(
        os.path.join(str(script_dir), 'pyi_symlinks_test.py'),
        pyi_args=add_data_args,
        app_args=['subdir', '--link-only'],
    )


# Test symbolic link pointing to a parent directory
def test_symlinks__parentdir__wholedir(tmpdir, script_dir, pyi_builder):
    # Create test data
    _create_data(tmpdir, 'orig_file.txt', os.path.join('subdir', 'linked_file.txt'))

    # Collect whole data directory
    data_dir = os.path.join(tmpdir, 'data')
    add_data_args = [
        '--add-data', data_dir + os.pathsep + 'data',
    ]  # yapf: disable

    # Run test script in 'parentdir' mode
    pyi_builder.test_script(
        os.path.join(str(script_dir), 'pyi_symlinks_test.py'),
        pyi_args=add_data_args,
        app_args=['parentdir'],
    )


# Test symbolic link pointing to a parent directory - symlink only
def test_symlinks__parentdir__symlink_only(tmpdir, script_dir, pyi_builder):
    # Create test data
    _create_data(tmpdir, 'orig_file.txt', os.path.join('subdir', 'linked_file.txt'))

    # Collect only symbolic link
    data_dir = os.path.join(tmpdir, 'data')
    add_data_args = [
        '--add-data', os.path.join(data_dir, 'subdir', 'linked_file.txt')
        + os.pathsep + os.path.join('data', 'subdir'),
    ]  # yapf: disable

    # Run test script in 'parentdir/link-only' mode
    pyi_builder.test_script(
        os.path.join(str(script_dir), 'pyi_symlinks_test.py'),
        pyi_args=add_data_args,
        app_args=['parentdir', '--link-only'],
    )
