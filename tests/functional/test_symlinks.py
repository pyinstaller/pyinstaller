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
import subprocess

import pytest

from PyInstaller.compat import is_win
from PyInstaller.utils.tests import create_symlink


# Test that bootloader is able to fully resolve a symlinked executable, on all OSes.
def test_bootloader_symlinked_executable(pyi_builder, tmp_path):
    pyi_builder.test_source(
        """
        import sys

        print(f"sys.argv={sys.argv}")
        print(f"sys.executable={sys.executable}")
        """
    )

    # Find executable and run additional tests with symbolic links
    print('------- Looking for executable. -------', file=sys.stderr)
    exes = pyi_builder._find_executables('test_source')
    assert len(exes) == 1
    executable = exes[0]
    print(f"True executable location: {executable}")

    exe_suffix = '.exe' if is_win else ''

    # Case #1: a relative symbolic link in a subdirectory
    print('------- Test case #1: relative symlink in subdirectory -------', file=sys.stderr)
    subdir = tmp_path / 'subdir'
    subdir.mkdir()

    symlink1 = subdir / f'relative-symlink-in-subdir{exe_suffix}'
    rel_link = os.path.relpath(executable, subdir)  # Compute relative link
    print(f"Relative symbolic link: {symlink1} -> {rel_link}", file=sys.stderr)

    create_symlink(rel_link, symlink1)

    subprocess.check_call([symlink1])

    # Case #2: an absolute symbolic link pointing to relative symbolic link from case #1.
    print('------- Test case #2: absolute symlink pointing to relative symlink -------', file=sys.stderr)
    symlink2 = tmp_path / f'absolute-symlink{exe_suffix}'
    print(f"Absolute symbolic link: {symlink2} -> {symlink1}", file=sys.stderr)

    create_symlink(symlink1, symlink2)

    subprocess.check_call([symlink2])


def _create_data(tmp_path, orig_filename, link_filename):
    # Create data directory
    data_path = tmp_path / "data"

    # Create original file
    abs_orig_filename = data_path / orig_filename
    abs_orig_filename.parent.mkdir(parents=True, exist_ok=True)
    abs_orig_filename.write_text("secret", encoding='utf-8')

    # Create symbolic link
    abs_linked_filename = data_path / link_filename
    abs_linked_filename.parent.mkdir(parents=True, exist_ok=True)
    rel_orig_filename = os.path.relpath(abs_orig_filename, abs_linked_filename.parent)

    create_symlink(rel_orig_filename, abs_linked_filename)


# Test collection of symlinked data files: the matrix below covers the three locations of the symbolic link relative
# to the original file (same directory, subdirectory, parent directory) crossed with what gets collected (both the
# original file and the symbolic link, only the symbolic link, or the whole data directory). Each parameter set is
# (orig_file, link_file, add_data, app_args), where:
#  * `orig_file` and `link_file` are the (os-separated) paths of the original file and the symbolic link, relative to
#    the data directory,
#  * `add_data` is a list of (source, destination) pairs for the --add-data arguments, with a `None` source meaning
#    "collect the whole data directory",
#  * `app_args` are the arguments passed to the test script, which selects its operating mode.
@pytest.mark.parametrize(
    "orig_file, link_file, add_data, app_args",
    [
        # Collect both symbolic link and file
        (
            ('orig_file.txt',), ('linked_file.txt',),
            [('orig_file.txt', 'data'), ('linked_file.txt', 'data')],
            ['samedir'],
        ),
        # Same as above, except that we collect the whole data directory instead of individual files
        (
            ('orig_file.txt',), ('linked_file.txt',),
            [(None, 'data')],
            ['samedir'],
        ),
        # Collect only symbolic link
        (
            ('orig_file.txt',), ('linked_file.txt',),
            [('linked_file.txt', 'data')],
            ['samedir', '--link-only'],
        ),
        # Collect symbolic link and original file, but place the latter somewhere else (this should effectively be the
        # same as 'link-only' scenario)
        (
            ('orig_file.txt',), ('linked_file.txt',),
            [('orig_file.txt', 'data2'), ('linked_file.txt', 'data')],
            ['samedir', '--link-only'],
        ),
        # Collect symbolic link and original file; collect original multiple times, in original and alternative
        # locations
        (
            ('orig_file.txt',), ('linked_file.txt',),
            [('orig_file.txt', 'data3'), ('orig_file.txt', 'data'), ('orig_file.txt', 'data2'),
             ('linked_file.txt', 'data')],
            ['samedir'],
        ),
        # Symbolic link pointing to a subdirectory; collect whole data directory
        (
            (os.path.join('subdir', 'orig_file.txt'),), ('linked_file.txt',),
            [(None, 'data')],
            ['subdir'],
        ),
        # Symbolic link pointing to a subdirectory; collect only symbolic link
        (
            (os.path.join('subdir', 'orig_file.txt'),), ('linked_file.txt',),
            [('linked_file.txt', 'data')],
            ['subdir', '--link-only'],
        ),
        # Symbolic link pointing to a parent directory; collect whole data directory
        (
            ('orig_file.txt',), (os.path.join('subdir', 'linked_file.txt'),),
            [(None, 'data')],
            ['parentdir'],
        ),
        # Symbolic link pointing to a parent directory; collect only symbolic link
        (
            ('orig_file.txt',), (os.path.join('subdir', 'linked_file.txt'),),
            [(os.path.join('subdir', 'linked_file.txt'), os.path.join('data', 'subdir'))],
            ['parentdir', '--link-only'],
        ),
    ],
    ids=[
        'samedir-symlink_and_file',
        'samedir-wholedir',
        'samedir-symlink_only',
        'samedir-orig_elsewhere',
        'samedir-orig_multiple',
        'subdir-wholedir',
        'subdir-symlink_only',
        'parentdir-wholedir',
        'parentdir-symlink_only',
    ],
)
def test_symlinks__collect(tmp_path, script_dir, pyi_builder, orig_file, link_file, add_data, app_args):
    # Create test data
    _create_data(tmp_path, *orig_file, *link_file)

    # Generate --add-data arguments; a `None` source means the whole data directory
    data_dir = tmp_path / 'data'
    add_data_args = []
    for src, dest in add_data:
        src_path = data_dir if src is None else data_dir / src
        add_data_args += ['--add-data', f"{src_path}:{dest}"]

    # Run test script
    pyi_builder.test_script(
        script_dir / 'pyi_symlinks_test.py',
        pyi_args=add_data_args,
        app_args=app_args,
    )


# The tests below verify the behavior when collecting chained symbolic links: file_d -> file_c -> file_b -> file_a.
#
# This reproduces the scenario found under Homebrew python environment on macOS, where shared libraries for `wxwidgets`
# have the following layout:
#  * libwx_baseu-3.2.0.2.1.dylib
#  * libwx_baseu-3.2.0.dylib -> libwx_baseu-3.2.0.2.1.dylib
#  * libwx_baseu-3.2.dylib -> libwx_baseu-3.2.0.dylib
#
# And only `libwx_baseu-3.2.0.2.1.dylib` and `libwx_baseu-3.2.dylib` end up referenced by other binaries, so the
# "intermediate" link is not collected. So to prevent the symlink to be collected as a duplicated copy (which leads to
# problems on macOS...), PyInstaller needs to be able to rewrite the link to "jump over" the missing intermediate link.


# Prepare the file and links for the test
def _prepare_chained_links_example(tmp_path):
    # Create data directory
    data_path = tmp_path / "data"
    data_path.mkdir()

    # Create original file: file_a
    (data_path / "file_a").write_text("secret", encoding='utf-8')

    # Create symbolic link: file_b -> file_a
    create_symlink("file_a", data_path / "file_b")

    # Create symbolic link: file_c -> file_b
    create_symlink("file_b", data_path / "file_c")

    # Create symbolic link: file_d -> file_c
    create_symlink("file_c", data_path / "file_d")

    return data_path


# Helper to generate --add-data arguments for PyInstaller.
def _collect_data(src_dir, filenames, dest_dir='.'):
    for filename in filenames:
        yield '--add-data'
        yield f"{src_dir / filename}:{dest_dir}"


def _chained_links_verification_source(regular_file, links):
    """
    Generate the frozen-app source that verifies the layout of collected chained symbolic links: `regular_file` must
    be collected as a regular file, and each (link, target) pair from `links` must be collected as a symbolic link
    pointing to `target`.
    """
    lines = [
        "import sys",
        "import os",
        "",
        f"# {regular_file} should be a regular file",
        f'{regular_file} = os.path.join(sys._MEIPASS, "{regular_file}")',
        f'assert os.path.isfile({regular_file}), "{regular_file} does not exist!"',
        f'assert not os.path.islink({regular_file}), "{regular_file} is a symbolic link, but should not be!"',
    ]
    for link, target in links:
        lines += [
            "",
            f"# {link} should be a symlink pointing to {target}",
            f'{link} = os.path.join(sys._MEIPASS, "{link}")',
            f'assert os.path.isfile({link}), "{link} does not exist!"',
            f'assert os.path.islink({link}), "{link} is not a symbolic link!"',
            f'assert os.readlink({link}) == "{target}", "{link} does not point to {target}!"',
        ]
    return "\n".join(f"        {line}" if line else line for line in lines) + "\n        "


# Each parameter set is (collected_files, regular_file, links): the files from `collected_files` are passed to
# --add-data, `regular_file` is expected to be collected as a regular file, and each (link, target) pair from `links`
# is expected to be collected as a symbolic link pointing to `target`.
@pytest.mark.parametrize(
    "collected_files, regular_file, links",
    [
        # Collect everything
        (
            ['file_a', 'file_b', 'file_c'], 'file_a',
            [('file_b', 'file_a'), ('file_c', 'file_b')],
        ),
        (
            ['file_a', 'file_b'], 'file_a',
            [('file_b', 'file_a')],
        ),
        (
            ['file_b', 'file_c'], 'file_b',
            [('file_c', 'file_b')],
        ),
        # Special case: PyInstaller needs to relink file_c to file_a due to missing link (file_b).
        (
            ['file_a', 'file_c'], 'file_a',
            [('file_c', 'file_a')],
        ),
        # Special case: PyInstaller needs to relink file_d to file_a due to missing links (file_b, file_c).
        (
            ['file_a', 'file_d'], 'file_a',
            [('file_d', 'file_a')],
        ),
        # Similar to the BC test case (file_b needs to be collected as a copy), but with a missing intermediate link
        # (file_c).
        (
            ['file_b', 'file_d'], 'file_b',
            [('file_d', 'file_b')],
        ),
    ],
    ids=['abc', 'ab', 'bc', 'ac', 'ad', 'bd'],
)
def test_symlinks__chained_links(tmp_path, pyi_builder, collected_files, regular_file, links):
    data_path = _prepare_chained_links_example(tmp_path)
    pyi_builder.test_source(
        _chained_links_verification_source(regular_file, links),
        pyi_args=list(_collect_data(data_path, collected_files)),
    )


# The tests below reproduce another quirk of the Homebrew python environments: the directories containing the shared
# libraries (and the corresponding versioned symbolic links) can themselves be linked to different locations, which can
# all be referenced from other binaries.
#
# For example, we have the following layout:
# * /usr/local/Cellar/wxwidgets/3.2.2.1_1/lib/libwx_baseu-3.2.0.2.1.dylib
# * /usr/local/Cellar/wxwidgets/3.2.2.1_1/lib/libwx_baseu-3.2.0.dylib -> libwx_baseu-3.2.0.2.1.dylib
# * /usr/local/Cellar/wxwidgets/3.2.2.1_1/lib/libwx_baseu-3.2.dylib -> libwx_baseu-3.2.0.dylib
# and
# * /usr/local/opt/wxwidgets/lib/libwx_baseu-3.2.0.2.1.dylib
# * /usr/local/opt/wxwidgets/lib/libwx_baseu-3.2.0.dylib -> libwx_baseu-3.2.0.2.1.dylib
# * /usr/local/opt/wxwidgets/lib/libwx_baseu-3.2.dylib -> libwx_baseu-3.2.0.dylib
# which are actually the same, because
# * /usr/local/opt/wxwidgets -> ../Cellar/wxwidgets/3.2.2.1_1
#
# Other binaries end up referencing `/usr/local/opt/wxwidgets/lib/libwx_baseu-3.2.dylib` and
# `/usr/local/Cellar/wxwidgets/3.2.2.1_1/lib/libwx_baseu-3.2.0.2.1.dylib`. So in addition the the problem with chained
# links and missing intermediate link, we also need to be able to handle the situation where the files appear to be
# originating from different locations due to the linking of parent directories.


# Prepare the file and links for the test
def _prepare_parent_directory_link_example(tmp_path):
    # Create data directory
    data_path = tmp_path / "data"

    # Create directory containing the actual files
    original_dir = data_path / 'original' / 'mydata' / 'v1.0.0'
    original_dir.mkdir(parents=True)

    # Create original file: file_a
    (original_dir / "file_a").write_text("secret", encoding='utf-8')

    # Create symbolic link: file_b -> file_a
    create_symlink("file_a", original_dir / "file_b")

    # Create symbolic link: file_c -> file_b
    create_symlink("file_b", original_dir / "file_c")

    # Create symbolic link: file_d -> file_c
    create_symlink("file_c", original_dir / "file_d")

    # Create a symbolic link at the directory level
    linked_dir = data_path / "linked"
    linked_dir.mkdir(parents=True)

    create_symlink(
        os.path.join('..', 'original', 'mydata', 'v1.0.0'),
        linked_dir / 'mydata-v1.0.0',
        target_is_directory=True,
    )

    return data_path


@pytest.mark.parametrize(
    "collected_files",
    [
        # Collect file_a from one directory and file_d from the other; this also causes missing intermediate links
        # (file_b, file_c).
        ['original/mydata/v1.0.0/file_a', 'linked/mydata-v1.0.0/file_d'],
        ['linked/mydata-v1.0.0/file_a', 'original/mydata/v1.0.0/file_d'],
    ],
    ids=['original', 'reversed'],
)
def test_symlinks__collect_chained_links_from_linked_directories(tmp_path, pyi_builder, collected_files):
    data_path = _prepare_parent_directory_link_example(tmp_path)
    pyi_builder.test_source(
        _chained_links_verification_source('file_a', [('file_d', 'file_a')]),
        pyi_args=list(_collect_data(data_path, collected_files)),
    )
