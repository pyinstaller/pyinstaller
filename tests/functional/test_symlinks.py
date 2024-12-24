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

    _create_symlink(rel_link, symlink1)

    subprocess.check_call([symlink1])

    # Case #2: an absolute symbolic link pointing to relative symbolic link from case #1.
    print('------- Test case #2: absolute symlink pointing to relative symlink -------', file=sys.stderr)
    symlink2 = tmp_path / f'absolute-symlink{exe_suffix}'
    print(f"Absolute symbolic link: {symlink2} -> {symlink1}", file=sys.stderr)

    _create_symlink(symlink1, symlink2)

    subprocess.check_call([symlink2])


# Wrapper for os.symlink that skips the test if symlink cannot be created on Windows.
def _create_symlink(src, dst, *args, **kwargs):
    # On Windows, symlinks need to use Windows-style backslashes, even if we are under msys2/mingw python that uses
    # POSIX-style separators. `src` might be a Path-like object, so explicitly convert it to string.
    if is_win and os.sep == '/':
        src = str(src).replace(os.sep, '\\')

    try:
        os.symlink(src, dst, **kwargs)
    except OSError:
        if is_win:
            pytest.skip("OS does not support creation of symbolic links.")
        else:
            raise


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

    _create_symlink(rel_orig_filename, abs_linked_filename)


# Collect both symbolic link and file
def test_symlinks__samedir__symlink_and_file(tmp_path, script_dir, pyi_builder):
    # Create test data
    _create_data(tmp_path, 'orig_file.txt', 'linked_file.txt')

    # Collect both original file and symbolic link
    data_dir = tmp_path / 'data'
    add_data_args = [
        '--add-data', f"{data_dir/'orig_file.txt'}:data",
        '--add-data', f"{data_dir/'linked_file.txt'}:data",
    ]  # yapf: disable

    # Run test script in 'samedir' mode
    pyi_builder.test_script(
        script_dir / 'pyi_symlinks_test.py',
        pyi_args=add_data_args,
        app_args=['samedir'],
    )


# Same as test_symlinks__samedir__symlink_and_file, except that we collect whole data directory instead of
# individual files.
def test_symlinks__samedir__wholedir(tmp_path, script_dir, pyi_builder):
    # Create test data
    _create_data(tmp_path, 'orig_file.txt', 'linked_file.txt')

    # Collect whole data directory
    data_dir = tmp_path / 'data'
    add_data_args = [
        '--add-data', f"{data_dir}:data",
    ]  # yapf: disable

    # Run test script in 'samedir' mode
    pyi_builder.test_script(
        script_dir / 'pyi_symlinks_test.py',
        pyi_args=add_data_args,
        app_args=['samedir'],
    )


# Collect only symbolic link
def test_symlinks__samedir__symlink_only(tmp_path, script_dir, pyi_builder):
    # Create test data
    _create_data(tmp_path, 'orig_file.txt', 'linked_file.txt')

    # Collect only symbolic link
    data_dir = tmp_path / 'data'
    add_data_args = [
        '--add-data', f"{data_dir / 'linked_file.txt'}:data",
    ]  # yapf: disable

    # Run test script in 'samedir/link-only' mode
    pyi_builder.test_script(
        script_dir / 'pyi_symlinks_test.py',
        pyi_args=add_data_args,
        app_args=['samedir', '--link-only'],
    )


# Collect symbolic link and original file, but place the latter somewhere else
def test_symlinks__samedir__orig_elsewhere(tmp_path, script_dir, pyi_builder):
    # Create test data
    _create_data(tmp_path, 'orig_file.txt', 'linked_file.txt')

    # Collect only symbolic link
    data_dir = tmp_path / 'data'
    add_data_args = [
        '--add-data', f"{data_dir / 'orig_file.txt'}:data2",
        '--add-data', f"{data_dir / 'linked_file.txt'}:data",
    ]  # yapf: disable

    # Run test script in 'samedir/link-only' mode (this should effectively be the same as 'link-only' scenario)
    pyi_builder.test_script(
        script_dir / 'pyi_symlinks_test.py',
        pyi_args=add_data_args,
        app_args=['samedir', '--link-only'],
    )


# Collect symbolic link and original file; collect original multiple times, in original and alternative locations.
def test_symlinks__samedir__orig_multiple(tmp_path, script_dir, pyi_builder):
    # Create test data
    _create_data(tmp_path, 'orig_file.txt', 'linked_file.txt')

    # Collect only symbolic link
    data_dir = tmp_path / 'data'
    add_data_args = [
        '--add-data', f"{data_dir / 'orig_file.txt'}:data3",
        '--add-data', f"{data_dir / 'orig_file.txt'}:data",
        '--add-data', f"{data_dir / 'orig_file.txt'}:data2",
        '--add-data', f"{data_dir / 'linked_file.txt'}:data",
    ]  # yapf: disable

    # Run test script in 'samedir' mode
    pyi_builder.test_script(
        script_dir / 'pyi_symlinks_test.py',
        pyi_args=add_data_args,
        app_args=['samedir'],
    )


# Test symbolic link pointing to a subdirectory
def test_symlinks__subdir__wholedir(tmp_path, script_dir, pyi_builder):
    # Create test data
    _create_data(tmp_path, os.path.join('subdir', 'orig_file.txt'), 'linked_file.txt')

    # Collect whole data directory
    data_dir = tmp_path / 'data'
    add_data_args = [
        '--add-data', f"{data_dir}:data",
    ]  # yapf: disable

    # Run test script in 'subdir' mode
    pyi_builder.test_script(
        script_dir / 'pyi_symlinks_test.py',
        pyi_args=add_data_args,
        app_args=['subdir'],
    )


# Test symbolic link pointing to a subdirectory - symlink only
def test_symlinks__subdir__symlink_only(tmp_path, script_dir, pyi_builder):
    # Create test data
    _create_data(tmp_path, os.path.join('subdir', 'orig_file.txt'), 'linked_file.txt')

    # Collect only symbolic link
    data_dir = tmp_path / 'data'
    add_data_args = [
        '--add-data', f"{data_dir / 'linked_file.txt'}:data",
    ]  # yapf: disable

    # Run test script in 'subdir/link-only' mode
    pyi_builder.test_script(
        script_dir / 'pyi_symlinks_test.py',
        pyi_args=add_data_args,
        app_args=['subdir', '--link-only'],
    )


# Test symbolic link pointing to a parent directory
def test_symlinks__parentdir__wholedir(tmp_path, script_dir, pyi_builder):
    # Create test data
    _create_data(tmp_path, 'orig_file.txt', os.path.join('subdir', 'linked_file.txt'))

    # Collect whole data directory
    data_dir = tmp_path / 'data'
    add_data_args = [
        '--add-data', f"{data_dir}:data",
    ]  # yapf: disable

    # Run test script in 'parentdir' mode
    pyi_builder.test_script(
        script_dir / 'pyi_symlinks_test.py',
        pyi_args=add_data_args,
        app_args=['parentdir'],
    )


# Test symbolic link pointing to a parent directory - symlink only
def test_symlinks__parentdir__symlink_only(tmp_path, script_dir, pyi_builder):
    # Create test data
    _create_data(tmp_path, 'orig_file.txt', os.path.join('subdir', 'linked_file.txt'))

    # Collect only symbolic link
    data_dir = tmp_path / 'data'
    add_data_args = [
        '--add-data', f"{data_dir / 'subdir' / 'linked_file.txt'}:{os.path.join('data', 'subdir')}",
    ]  # yapf: disable

    # Run test script in 'parentdir/link-only' mode
    pyi_builder.test_script(
        script_dir / 'pyi_symlinks_test.py',
        pyi_args=add_data_args,
        app_args=['parentdir', '--link-only'],
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
    _create_symlink("file_a", data_path / "file_b")

    # Create symbolic link: file_c -> file_b
    _create_symlink("file_b", data_path / "file_c")

    # Create symbolic link: file_d -> file_c
    _create_symlink("file_c", data_path / "file_d")

    return data_path


# Helper to generate --add-data arguments for PyInstaller.
def _collect_data(src_dir, filenames, dest_dir='.'):
    for filename in filenames:
        yield '--add-data'
        yield f"{src_dir / filename}:{dest_dir}"


def test_symlinks__chained_links_abc(tmp_path, pyi_builder):
    data_path = _prepare_chained_links_example(tmp_path)
    collected_files = ['file_a', 'file_b', 'file_c']
    pyi_builder.test_source(
        """
        import sys
        import os

        # file_a should be a regular file
        file_a = os.path.join(sys._MEIPASS, "file_a")
        assert os.path.isfile(file_a), "file_a does not exist!"
        assert not os.path.islink(file_a), "file_a is a symbolic link, but should not be!"

        # file_b should be a symlink pointing to file_a
        file_b = os.path.join(sys._MEIPASS, "file_b")
        assert os.path.isfile(file_b), "file_b does not exist!"
        assert os.path.islink(file_b), "file_b is not a symbolic link!"
        assert os.readlink(file_b) == "file_a", "file_b does not point to file_a!"

        # file_c should be a symlink pointing to file_b
        file_c = os.path.join(sys._MEIPASS, "file_c")
        assert os.path.isfile(file_c), "file_c does not exist!"
        assert os.path.islink(file_c), "file_c is not a symbolic link!"
        assert os.readlink(file_c) == "file_b", "file_c does not point to file_b!"
        """,
        pyi_args=list(_collect_data(data_path, collected_files))
    )


def test_symlinks__chained_links_ab(tmp_path, pyi_builder):
    data_path = _prepare_chained_links_example(tmp_path)
    collected_files = ['file_a', 'file_b']
    pyi_builder.test_source(
        """
        import sys
        import os

        # file_a should be a regular file
        file_a = os.path.join(sys._MEIPASS, "file_a")
        assert os.path.isfile(file_a), "file_a does not exist!"
        assert not os.path.islink(file_a), "file_a is a symbolic link, but should not be!"

        # file_b should be a symlink pointing to file_a
        file_b = os.path.join(sys._MEIPASS, "file_b")
        assert os.path.isfile(file_b), "file_b does not exist!"
        assert os.path.islink(file_b), "file_b is not a symbolic link!"
        assert os.readlink(file_b) == "file_a", "file_b does not point to file_a!"
        """,
        pyi_args=list(_collect_data(data_path, collected_files))
    )


def test_symlinks__chained_links_bc(tmp_path, pyi_builder):
    data_path = _prepare_chained_links_example(tmp_path)
    collected_files = ['file_b', 'file_c']
    pyi_builder.test_source(
        """
        import sys
        import os

        # file_b should be a regular file
        file_b = os.path.join(sys._MEIPASS, "file_b")
        assert os.path.isfile(file_b), "file_b does not exist!"
        assert not os.path.islink(file_b), "file_b is a symbolic link, but should not be!"

        # file_c should be a symlink pointing to file_b
        file_c = os.path.join(sys._MEIPASS, "file_c")
        assert os.path.isfile(file_c), "file_c does not exist!"
        assert os.path.islink(file_c), "file_c is not a symbolic link!"
        assert os.readlink(file_c) == "file_b", "file_c does not point to file_b!"
        """,
        pyi_args=list(_collect_data(data_path, collected_files))
    )


# This is a special case, because PyInstaller needs to relink file_c to file_a due to missing link (file_b).
def test_symlinks__chained_links_ac(tmp_path, pyi_builder):
    data_path = _prepare_chained_links_example(tmp_path)
    collected_files = ['file_a', 'file_c']
    pyi_builder.test_source(
        """
        import sys
        import os

        # file_a should be a regular file
        file_a = os.path.join(sys._MEIPASS, "file_a")
        assert os.path.isfile(file_a), "file_a does not exist!"
        assert not os.path.islink(file_a), "file_a is a symbolic link, but should not be!"

        # file_c should be a symlink pointing to file_a
        file_c = os.path.join(sys._MEIPASS, "file_c")
        assert os.path.isfile(file_c), "file_c does not exist!"
        assert os.path.islink(file_c), "file_c is not a symbolic link!"
        assert os.readlink(file_c) == "file_a", "file_c does not point to file_a!"
        """,
        pyi_args=list(_collect_data(data_path, collected_files))
    )


# This is a special case, because PyInstaller needs to relink file_d to file_a due to missing links (file_b, file_c).
def test_symlinks__chained_links_ad(tmp_path, pyi_builder):
    data_path = _prepare_chained_links_example(tmp_path)
    collected_files = ['file_a', 'file_d']
    pyi_builder.test_source(
        """
        import sys
        import os

        # file_a should be a regular file
        file_a = os.path.join(sys._MEIPASS, "file_a")
        assert os.path.isfile(file_a), "file_a does not exist!"
        assert not os.path.islink(file_a), "file_a is a symbolic link, but should not be!"

        # file_d should be a symlink pointing to file_a
        file_d = os.path.join(sys._MEIPASS, "file_d")
        assert os.path.isfile(file_d), "file_d does not exist!"
        assert os.path.islink(file_d), "file_d is not a symbolic link!"
        assert os.readlink(file_d) == "file_a", "file_d does not point to file_a!"
        """,
        pyi_args=list(_collect_data(data_path, collected_files))
    )


# Similar to the BC test case (file_b needs to be collected as a copy), but with a missing intermediate link (file_c).
def test_symlinks__chained_links_bd(tmp_path, pyi_builder):
    data_path = _prepare_chained_links_example(tmp_path)
    collected_files = ['file_b', 'file_d']
    pyi_builder.test_source(
        """
        import sys
        import os

        # file_b should be a regular file
        file_b = os.path.join(sys._MEIPASS, "file_b")
        assert os.path.isfile(file_b), "file_b does not exist!"
        assert not os.path.islink(file_b), "file_b is a symbolic link, but should not be!"

        # file_d should be a symlink pointing to file_b
        file_d = os.path.join(sys._MEIPASS, "file_d")
        assert os.path.isfile(file_d), "file_d does not exist!"
        assert os.path.islink(file_d), "file_d is not a symbolic link!"
        assert os.readlink(file_d) == "file_b", "file_d does not point to file_b!"
        """,
        pyi_args=list(_collect_data(data_path, collected_files))
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
    _create_symlink("file_a", original_dir / "file_b")

    # Create symbolic link: file_c -> file_b
    _create_symlink("file_b", original_dir / "file_c")

    # Create symbolic link: file_d -> file_c
    _create_symlink("file_c", original_dir / "file_d")

    # Create a symbolic link at the directory level
    linked_dir = data_path / "linked"
    linked_dir.mkdir(parents=True)

    _create_symlink(
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
        """
        import sys
        import os

        # file_a should be a regular file
        file_a = os.path.join(sys._MEIPASS, "file_a")
        assert os.path.isfile(file_a), "file_a does not exist!"
        assert not os.path.islink(file_a), "file_a is a symbolic link, but should not be!"

        # file_d should be a symlink pointing to file_a
        file_d = os.path.join(sys._MEIPASS, "file_d")
        assert os.path.isfile(file_d), "file_d does not exist!"
        assert os.path.islink(file_d), "file_d is not a symbolic link!"
        assert os.readlink(file_d) == "file_a", "file_d does not point to file_a!"
        """,
        pyi_args=list(_collect_data(data_path, collected_files))
    )
