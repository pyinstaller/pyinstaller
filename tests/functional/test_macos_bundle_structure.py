#-----------------------------------------------------------------------------
# Copyright (c) 2022-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
#
# Basic tests for macOS app bundle data relocation and code signing.

import os  # for `os.readlink`, because `pathlib.Path.readlink` is not available in python 3.8
import plistlib

import pytest

from PyInstaller.utils.tests import importorskip, onedir_only
from PyInstaller.building.osx import DOT_REPLACEMENT

# NOTE: the tests below explicitly enable the following environment variables:
#  PYINSTALLER_STRICT_BUNDLE_CODESIGN_ERROR: have codesign errors terminate the build instead of generating a warning.
#  PYINSTALLER_VERIFY_BUNDLE_SIGNATURE: perform strict verification of signature and signature-related data.
# We have these enabled globally on our CI (to cover all macOS .app bundle builds), but we explicitly apply them here
# for off-line test runs.


# Test that collected metadata is properly relocated to avoid codesign errors due to directory containing dots in name.
@pytest.mark.darwin
@importorskip('psutil')
@onedir_only
def test_macos_bundle_signing_metadata(pyi_builder, monkeypatch):
    monkeypatch.setenv("PYINSTALLER_STRICT_BUNDLE_CODESIGN_ERROR", "1")
    monkeypatch.setenv("PYINSTALLER_VERIFY_BUNDLE_SIGNATURE", "1")

    pyi_builder.test_source("""
        import psutil
        """, pyi_args=['--windowed', '--copy-metadata', 'psutil'])


# Test that the bundle signing works even if we collect a package as source .py files, which we do not relocate.
@pytest.mark.darwin
@importorskip('psutil')
@onedir_only
def test_macos_bundle_signing_py_files(pyi_builder, monkeypatch):
    monkeypatch.setenv("PYINSTALLER_STRICT_BUNDLE_CODESIGN_ERROR", "1")
    monkeypatch.setenv("PYINSTALLER_VERIFY_BUNDLE_SIGNATURE", "1")

    # Override Analysis so that we can set package collection mode without having to use .spec file.
    def AnalysisOverride(*args, **kwargs):
        kwargs['module_collection_mode'] = {'psutil': 'py'}
        return Analysis(*args, **kwargs)

    import PyInstaller.building.build_main
    Analysis = PyInstaller.building.build_main.Analysis
    monkeypatch.setattr('PyInstaller.building.build_main.Analysis', AnalysisOverride)

    pyi_builder.test_source("""
        import psutil
        """, pyi_args=['--windowed'])


# Test that the codesigning works even if we collect a package as .pyc files, which we do not relocate.
@pytest.mark.darwin
@importorskip('psutil')
@onedir_only
def test_macos_bundle_signing_pyc_files(pyi_builder, monkeypatch):
    monkeypatch.setenv("PYINSTALLER_STRICT_BUNDLE_CODESIGN_ERROR", "1")
    monkeypatch.setenv("PYINSTALLER_VERIFY_BUNDLE_SIGNATURE", "1")

    # Override Analysis so that we can set package collection mode without having to use .spec file.
    def AnalysisOverride(*args, **kwargs):
        kwargs['module_collection_mode'] = {'psutil': 'pyc'}
        return Analysis(*args, **kwargs)

    import PyInstaller.building.build_main
    Analysis = PyInstaller.building.build_main.Analysis
    monkeypatch.setattr('PyInstaller.building.build_main.Analysis', AnalysisOverride)

    pyi_builder.test_source("""
        import psutil
        """, pyi_args=['--windowed'])


# The following tests explicitly check the structure of generated macOS .app bundles w.r.t. binaries and data resources
# (re)location and cross-linking.


def _create_app_bundle(pyi_builder, monkeypatch, tmp_path, datas=None, binaries=None):
    monkeypatch.setenv("PYINSTALLER_STRICT_BUNDLE_CODESIGN_ERROR", "1")
    monkeypatch.setenv("PYINSTALLER_VERIFY_BUNDLE_SIGNATURE", "1")

    extra_args = []
    for src_name, dest_name in datas or []:
        extra_args += ['--add-data', f"{src_name}:{dest_name}"]
    for src_name, dest_name in binaries or []:
        extra_args += ['--add-binary', f"{src_name}:{dest_name}"]

    pyi_builder.test_source("""
        print("Hello world!")
        """, pyi_args=['--windowed', *extra_args])

    # Return path to the generated .app bundle, so calling test can inspect it
    return tmp_path / 'dist' / 'test_source.app'


def _create_test_data_file(filename):
    filename.parent.mkdir(parents=True, exist_ok=True)
    # Create a text file
    filename.write_text("Test file", encoding='utf-8')


def _create_test_binary(filename):
    filename.parent.mkdir(parents=True, exist_ok=True)
    # Copy _struct extension
    import _struct
    import shutil
    shutil.copy2(_struct.__file__, filename)


def _create_test_framework(bundle_path):
    # Infer binary name from .framework bundle name.
    assert bundle_path.name.endswith('.framework')
    binary_name = bundle_path.name[:-10]

    binary_path = bundle_path / 'Versions' / 'A' / binary_name
    _create_test_binary(binary_path)

    # Create basic `Info.plist`.
    resources_path = bundle_path / 'Versions' / 'A' / 'Resources'
    resources_path.mkdir(parents=True, exist_ok=True)

    info_plist_file = resources_path / 'Info.plist'

    info_plist = {
        'CFBundleExecutable': binary_name,
        'CFBundleIdentifier': f'org.pyinstaller.{binary_name}',
        'CFBundlePackageType': 'FMWK',
        'CFBundleShortVersionString': '1.0',
        'CFBundleSignature': '????',
        'CFBundleVersion': '1.0.0',
    }

    with open(info_plist_file, "wb") as fp:
        plistlib.dump(info_plist, fp)


# Test that top-level data file is relocated into `Contents/Resources` and symlinked back into `Contents/Frameworks`.
@pytest.mark.darwin
@onedir_only
def test_macos_bundle_layout_data_file(pyi_builder, monkeypatch, tmp_path):
    datas = []

    src_path = tmp_path / 'data_file.txt'
    _create_test_data_file(src_path)
    datas.append((src_path, '.'))

    bundle_path = _create_app_bundle(pyi_builder, monkeypatch, tmp_path, datas=datas)

    # The data file is placed into `Contents/Resources`...
    check_path = bundle_path / 'Contents' / 'Resources' / 'data_file.txt'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    # ... and symlinked into `Contents/MacOS`.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'data_file.txt'
    assert check_path.is_symlink()
    assert check_path.is_file()  # Is link valid?
    assert os.readlink(check_path) == '../Resources/data_file.txt'


# Test that top-level binary is kept in `Contents/Frameworks` and symlinked into `Contents/Resources`.
@pytest.mark.darwin
@onedir_only
def test_macos_bundle_layout_binary(pyi_builder, monkeypatch, tmp_path):
    binaries = []

    src_path = tmp_path / 'binary.dylib'
    _create_test_binary(src_path)
    binaries.append((src_path, '.'))

    bundle_path = _create_app_bundle(pyi_builder, monkeypatch, tmp_path, binaries=binaries)

    # The binary is placed into `Contents/Frameworks`...
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'binary.dylib'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    # ... and symlinked into `Contents/Resources`.
    check_path = bundle_path / 'Contents' / 'Resources' / 'binary.dylib'
    assert check_path.is_symlink()
    assert check_path.is_file()  # Is link valid?
    assert os.readlink(check_path) == '../Frameworks/binary.dylib'


# Test that data-only directory is relocated into `Contents/Resources` and symlinked back into `Contents/Frameworks`.
@pytest.mark.darwin
@onedir_only
def test_macos_bundle_layout_data_only_dir(pyi_builder, monkeypatch, tmp_path):
    datas = []

    # + data_dir: (1)
    #    - data_file1.txt (2)
    #    - data_file2.txt (3)
    src_path = tmp_path / 'data_dir' / 'data_file1.txt'
    _create_test_data_file(src_path)
    datas.append((src_path, 'data_dir'))

    src_path = tmp_path / 'data_dir' / 'data_file2.txt'
    _create_test_data_file(src_path)
    datas.append((src_path, 'data_dir'))

    bundle_path = _create_app_bundle(pyi_builder, monkeypatch, tmp_path, datas=datas)

    # (1) The whole data directory is placed into `Contents/Resources`...
    check_path = bundle_path / 'Contents' / 'Resources' / 'data_dir'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    # ... and symlinked (at directory level) into `Contents/Frameworks`.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'data_dir'
    assert check_path.is_dir()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == '../Resources/data_dir'

    # (2) The data file is placed into directory in `Contents/Resources`...
    check_path = bundle_path / 'Contents' / 'Resources' / 'data_dir' / 'data_file1.txt'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    # ... but it is also reachable from `Contents/Frameworks`. The linking is done at the parent directory level, so
    # the file itself is NOT seen as a symlink.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'data_dir' / 'data_file1.txt'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    # (3) Same goes for the second data file.
    check_path = bundle_path / 'Contents' / 'Resources' / 'data_dir' / 'data_file2.txt'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    check_path = bundle_path / 'Contents' / 'Frameworks' / 'data_dir' / 'data_file2.txt'
    assert check_path.is_file()
    assert not check_path.is_symlink()


# Test that binary-only directory is kept in `Contents/Frameworks` and symlinked into `Contents/Resources`.
@pytest.mark.darwin
@onedir_only
def test_macos_bundle_layout_binary_only_dir(pyi_builder, monkeypatch, tmp_path):
    binaries = []

    # + binary_dir: (1)
    #    - binary1.dylib (2)
    #    - binary2.dylib (3)
    src_path = tmp_path / 'binary_dir' / 'binary1.dylib'
    _create_test_binary(src_path)
    binaries.append((src_path, 'binary_dir'))

    src_path = tmp_path / 'binary_dir' / 'binary2.dylib'
    _create_test_binary(src_path)
    binaries.append((src_path, 'binary_dir'))

    bundle_path = _create_app_bundle(pyi_builder, monkeypatch, tmp_path, binaries=binaries)

    # (1) The whole binary directory is placed into `Contents/Frameworks`...
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'binary_dir'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    # ... and symlinked (at directory level) into Contents/Resources.
    check_path = bundle_path / 'Contents' / 'Resources' / 'binary_dir'
    assert check_path.is_dir()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == '../Frameworks/binary_dir'

    # (2) The binary file is placed into directory in `Contents/Frameworks`...
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'binary_dir' / 'binary1.dylib'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    # ... but it is also reachable from `Resources/Frameworks`. The linking is done at the parent directory level,
    # so the file itself is NOT seen as a symlink.
    check_path = bundle_path / 'Contents' / 'Resources' / 'binary_dir' / 'binary1.dylib'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    # (3) Same goes for the second binary file.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'binary_dir' / 'binary2.dylib'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    check_path = bundle_path / 'Contents' / 'Resources' / 'binary_dir' / 'binary2.dylib'
    assert check_path.is_file()
    assert not check_path.is_symlink()


# Test that mxied-content directory is created in both `Contents/Frameworks` and `Contents/Resources`, and that files
# are put into the proper directory and cross-linked into the other directory.
@pytest.mark.darwin
@onedir_only
def test_macos_bundle_layout_mixed_dir(pyi_builder, monkeypatch, tmp_path):
    datas = []
    binaries = []

    # + mixed_dir: (1)
    #    - data_file.txt (2)
    #    - binary.dylib (3)
    src_path = tmp_path / 'mixed_dir' / 'data_file.txt'
    _create_test_data_file(src_path)
    datas.append((src_path, 'mixed_dir'))

    src_path = tmp_path / 'mixed_dir' / 'binary.dylib'
    _create_test_binary(src_path)
    binaries.append((src_path, 'mixed_dir'))

    bundle_path = _create_app_bundle(pyi_builder, monkeypatch, tmp_path, datas=datas, binaries=binaries)

    # (1) The mixed-content directory is created in both `Contents/Frameworks` and `Contents/Resources` (i.e., no
    # linking at the directory level).
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'mixed_dir'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    check_path = bundle_path / 'Contents' / 'Resources' / 'mixed_dir'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    # (2) The data file is placed into directory in `Contents/Resources`...
    check_path = bundle_path / 'Contents' / 'Resources' / 'mixed_dir' / 'data_file.txt'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    # ... and symlinked into directory in `Contents/Frameworks`.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'mixed_dir' / 'data_file.txt'
    assert check_path.is_file()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == '../../Resources/mixed_dir/data_file.txt'

    # (3) The binary is placed into directory in `Contents/Frameworks`...
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'mixed_dir' / 'binary.dylib'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    # ... and symlinked into directory in `Contents/Resources`.
    check_path = bundle_path / 'Contents' / 'Resources' / 'mixed_dir' / 'binary.dylib'
    assert check_path.is_file()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == '../../Frameworks/mixed_dir/binary.dylib'


# Repeat the test with mixed-content directory, except that it now contains three sub-directories: a data-only one,
# a binary-only one, and mixed-content one.
@pytest.mark.darwin
@onedir_only
def test_macos_bundle_layout_mixed_dir_with_subdirs(pyi_builder, monkeypatch, tmp_path):
    datas = []
    binaries = []

    # + mixed_dir: (1)
    #    + data_subdir: (2)
    #       - data_file.txt (3)
    #    + binary_subdir: (4)
    #       - binary.dylib (5)
    #    + mixed_subdir: (6)
    #       - data_file.txt (7)
    #       - binary.dylib (8)
    src_path = tmp_path / 'mixed_dir' / 'data_subdir' / 'data_file.txt'
    _create_test_data_file(src_path)
    datas.append((src_path, 'mixed_dir/data_subdir'))

    src_path = tmp_path / 'mixed_dir' / 'binary_subdir' / 'binary.dylib'
    _create_test_binary(src_path)
    binaries.append((src_path, 'mixed_dir/binary_subdir'))

    src_path = tmp_path / 'mixed_dir' / 'mixed_subdir' / 'data_file.txt'
    _create_test_data_file(src_path)
    datas.append((src_path, 'mixed_dir/mixed_subdir'))

    src_path = tmp_path / 'mixed_dir' / 'mixed_subdir' / 'binary.dylib'
    _create_test_binary(src_path)
    binaries.append((src_path, 'mixed_dir/mixed_subdir'))

    bundle_path = _create_app_bundle(pyi_builder, monkeypatch, tmp_path, datas=datas, binaries=binaries)

    # (1) The mixed-content directory is created in both `Contents/Frameworkds` and `Contents/Resources` (i.e., no
    # linking at the directory level).
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'mixed_dir'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    check_path = bundle_path / 'Contents' / 'Resources' / 'mixed_dir'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    # (2) The whole data sub-directory is placed into directory in `Contents/Resources`...
    check_path = bundle_path / 'Contents' / 'Resources' / 'mixed_dir' / 'data_subdir'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    # ... and symlinked (at directory level) into directory in `Contents/Frameworks`.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'mixed_dir' / 'data_subdir'
    assert check_path.is_dir()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == '../../Resources/mixed_dir/data_subdir'

    # (3) The data file is placed into data sub-directory in `Contents/Resources`...
    check_path = bundle_path / 'Contents' / 'Resources' / 'mixed_dir' / 'data_subdir' / 'data_file.txt'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    # ... but it is also reachable from `Contents/Frameworks`. The linking is done at the parent directory level, so
    # the file itself is NOT seen as a symlink.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'mixed_dir' / 'data_subdir' / 'data_file.txt'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    # (4) The whole binary sub-directory is placed into directory in `Contents/Frameworks`...
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'mixed_dir' / 'binary_subdir'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    # ... and symlinked (at directory level) into directory in `Contents/Resources`.
    check_path = bundle_path / 'Contents' / 'Resources' / 'mixed_dir' / 'binary_subdir'
    assert check_path.is_dir()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == '../../Frameworks/mixed_dir/binary_subdir'

    # (5) The binary file is placed into directory in `Contents/Frameworks`...
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'mixed_dir' / 'binary_subdir' / 'binary.dylib'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    # ... but it is also reachable from `Resources/Frameworks`. The linking is done at the parent directory level,
    # so the file itself is NOT seen as a symlink.
    check_path = bundle_path / 'Contents' / 'Resources' / 'mixed_dir' / 'binary_subdir' / 'binary.dylib'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    # (6) The mixed-content sub-directory is created in both `Contents/Frameworks` and `Contents/Resources` (i.e., no
    # linking at the directory level).
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'mixed_dir' / 'mixed_subdir'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    check_path = bundle_path / 'Contents' / 'Resources' / 'mixed_dir' / 'mixed_subdir'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    # (7) The data file is placed into directory in `Contents/Resources`...
    check_path = bundle_path / 'Contents' / 'Resources' / 'mixed_dir' / 'mixed_subdir' / 'data_file.txt'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    # ... and symlinked into directory in `Contents/Frameworks`.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'mixed_dir' / 'mixed_subdir' / 'data_file.txt'
    assert check_path.is_file()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == '../../../Resources/mixed_dir/mixed_subdir/data_file.txt'

    # (3) The binary is placed into directory in `Contents/Frameworks`...
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'mixed_dir' / 'mixed_subdir' / 'binary.dylib'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    # ... and symlinked into directory in `Contents/Resources`.
    check_path = bundle_path / 'Contents' / 'Resources' / 'mixed_dir' / 'mixed_subdir' / 'binary.dylib'
    assert check_path.is_file()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == '../../../Frameworks/mixed_dir/mixed_subdir/binary.dylib'


# Repeat the test with mixed-content directory and sub-directories, except that all directories now contain a dot in
# their names.
@pytest.mark.darwin
@onedir_only
def test_macos_bundle_layout_mixed_dir_with_subdirs_and_dots(pyi_builder, monkeypatch, tmp_path):
    datas = []
    binaries = []

    # + mixed.dir: (1)
    #    + .data_subdir: (2)
    #       - data_file.txt (3)
    #    + .binary_subdir: (4)
    #       - binary.dylib (5)
    #    + mixed_subdir.: (6)
    #       - data_file.txt (7)
    #       - binary.dylib (8)
    src_path = tmp_path / 'mixed.dir' / '.data_subdir' / 'data_file.txt'
    _create_test_data_file(src_path)
    datas.append((src_path, 'mixed.dir/.data_subdir'))

    src_path = tmp_path / 'mixed.dir' / '.binary_subdir' / 'binary.dylib'
    _create_test_binary(src_path)
    binaries.append((src_path, 'mixed.dir/.binary_subdir'))

    src_path = tmp_path / 'mixed.dir' / 'mixed_subdir.' / 'data_file.txt'
    _create_test_data_file(src_path)
    datas.append((src_path, 'mixed.dir/mixed_subdir.'))

    src_path = tmp_path / 'mixed.dir' / 'mixed_subdir.' / 'binary.dylib'
    _create_test_binary(src_path)
    binaries.append((src_path, 'mixed.dir/mixed_subdir.'))

    bundle_path = _create_app_bundle(pyi_builder, monkeypatch, tmp_path, datas=datas, binaries=binaries)

    # (1) The mixed-content directory is created in both `Contents/Frameworks` and `Contents/Resources` (i.e., no
    # linking at the directory level). For directory in `Contents/MacOS`, the `.` in the name is replaced with
    # `DOT_REPLACEMENT`, and a symlink is created from original name to the modified one. For directory in
    # `Contents/Resources`, this is not necessary.
    check_path = bundle_path / 'Contents' / 'Frameworks' / f'mixed{DOT_REPLACEMENT}dir'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    check_path = bundle_path / 'Contents' / 'Frameworks' / 'mixed.dir'
    assert check_path.is_dir()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == f'mixed{DOT_REPLACEMENT}dir'

    check_path = bundle_path / 'Contents' / 'Resources' / 'mixed.dir'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    check_path = bundle_path / 'Contents' / 'Resources' / f'mixed{DOT_REPLACEMENT}dir'
    assert not check_path.exists()

    # (2) The whole data sub-directory is placed into directory in `Contents/Resources`. There is no need for name
    # moficiation here.
    check_path = bundle_path / 'Contents' / 'Resources' / 'mixed.dir' / '.data_subdir'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    check_path = bundle_path / 'Contents' / 'Resources' / 'mixed.dir' / f'{DOT_REPLACEMENT}data_subdir'
    assert not check_path.exists()

    # The data sub-directory is symlinked (at directory level) into directory in `Contents/Frameworks`. Due to this
    # being a symlink, we do not need name modification here, either.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'mixed.dir' / '.data_subdir'
    assert check_path.is_dir()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == '../../Resources/mixed.dir/.data_subdir'

    check_path = bundle_path / 'Contents' / 'Frameworks' / 'mixed.dir' / f'{DOT_REPLACEMENT}data_subdir'
    assert not check_path.exists()

    # (3) The data file is placed into data sub-directory in `Contents/Resources`...
    check_path = bundle_path / 'Contents' / 'Resources' / 'mixed.dir' / '.data_subdir' / 'data_file.txt'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    # ... but it is also reachable from `Contents/Frameworks`. The linking is done at the parent directory level,
    # so the file itself is NOT seen as a symlink.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'mixed.dir' / '.data_subdir' / 'data_file.txt'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    # (4) The whole binary sub-directory is placed into directory in `Contents/Frameworks`. Due to the dot in the name,
    # the directory is created with modified name (`.` replaced by `DOT_REPLACEMENT`). A symlink is created from
    # original name to the modified one.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'mixed.dir' / f'{DOT_REPLACEMENT}binary_subdir'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    check_path = bundle_path / 'Contents' / 'Frameworks' / 'mixed.dir' / '.binary_subdir'
    assert check_path.is_dir()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == f'{DOT_REPLACEMENT}binary_subdir'

    # A symlink (at directory level) is also created into directory in `Contents/Resources`.
    check_path = bundle_path / 'Contents' / 'Resources' / 'mixed.dir' / '.binary_subdir'
    assert check_path.is_dir()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == '../../Frameworks/mixed.dir/.binary_subdir'

    check_path = bundle_path / 'Contents' / 'Resources' / 'mixed.dir' / f'{DOT_REPLACEMENT}binary_subdir'
    assert not check_path.exists()

    # (5) The binary file is placed into directory in `Contents/Frameworks`...
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'mixed.dir' / '.binary_subdir' / 'binary.dylib'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    # ... but it is also reachable from `Resources/Frameworks`. The linking is done at the parent directory level,
    # so the file itself is NOT seen as a symlink.
    check_path = bundle_path / 'Contents' / 'Resources' / 'mixed.dir' / '.binary_subdir' / 'binary.dylib'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    # (6) The mixed-content sub-directory is created in both `Contents/Frameworks` and `Contents/Resources` (i.e., no
    # linking at the directory level). The directory in `Contents/MacOS` requires special handling due to dot in the
    # name (replacement of `.` with `DOT_REPLACEMENT`, and symlink from original to modified name), while the directory
    # in `Contents/Resources` does not.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'mixed.dir' / f'mixed_subdir{DOT_REPLACEMENT}'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    check_path = bundle_path / 'Contents' / 'Frameworks' / 'mixed.dir' / 'mixed_subdir.'
    assert check_path.is_dir()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == f'mixed_subdir{DOT_REPLACEMENT}'

    check_path = bundle_path / 'Contents' / 'Resources' / 'mixed.dir' / 'mixed_subdir.'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    check_path = bundle_path / 'Contents' / 'Resources' / 'mixed.dir' / f'mixed_subdir{DOT_REPLACEMENT}'
    assert not check_path.exists()

    # (7) The data file is placed into directory in `Contents/Resources`...
    check_path = bundle_path / 'Contents' / 'Resources' / 'mixed.dir' / 'mixed_subdir.' / 'data_file.txt'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    # ... and symlinked into directory in `Contents/Frameworks`.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'mixed.dir' / 'mixed_subdir.' / 'data_file.txt'
    assert check_path.is_file()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == '../../../Resources/mixed.dir/mixed_subdir./data_file.txt'

    # (3) The binary is placed into directory in `Contents/Frameworks`...
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'mixed.dir' / 'mixed_subdir.' / 'binary.dylib'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    # ... and symlinked into directory in `Contents/Resources`.
    check_path = bundle_path / 'Contents' / 'Resources' / 'mixed.dir' / 'mixed_subdir.' / 'binary.dylib'
    assert check_path.is_file()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == '../../../Frameworks/mixed.dir/mixed_subdir./binary.dylib'


# Test with symlink in top-level directory pointing to a data file in data-only directory.
@pytest.mark.darwin
@onedir_only
def test_macos_bundle_layout_symlink_into_data_dir(pyi_builder, monkeypatch, tmp_path):
    datas = []

    # + data_dir: (1)
    #    - data_file.txt (2)
    # - link_to_data.txt -> data_dir/data_file.txt (3)
    src_path = tmp_path / 'data_dir' / 'data_file.txt'
    _create_test_data_file(src_path)
    datas.append((src_path, 'data_dir'))

    src_path = tmp_path / 'link_to_data_file.txt'
    src_path.symlink_to('data_dir/data_file.txt')
    datas.append((src_path, '.'))

    bundle_path = _create_app_bundle(pyi_builder, monkeypatch, tmp_path, datas=datas)

    # (1) The whole data directory is placed into `Contents/Resources`...
    check_path = bundle_path / 'Contents' / 'Resources' / 'data_dir'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    # ... and symlinked (at directory level) into `Contents/Frameworks`.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'data_dir'
    assert check_path.is_dir()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == '../Resources/data_dir'

    # (2) The data file is placed into directory in `Contents/Resources`...
    check_path = bundle_path / 'Contents' / 'Resources' / 'data_dir' / 'data_file.txt'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    # ... but it is also reachable from `Contents/Frameworks`. The linking is done at the parent directory level,
    # so the file itself is NOT seen as a symlink.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'data_dir' / 'data_file.txt'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    # (3) The symlink is replicated in both `Contents/Frameworks` and `Contents/Resources`, and points to the resource
    # (file or symlink) in the same directory.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'link_to_data_file.txt'
    assert check_path.is_file()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == 'data_dir/data_file.txt'

    check_path = bundle_path / 'Contents' / 'Resources' / 'link_to_data_file.txt'
    assert check_path.is_file()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == 'data_dir/data_file.txt'


# Test with symlink in top-level directory pointing to a binary in binary-only directory.
@pytest.mark.darwin
@onedir_only
def test_macos_bundle_layout_symlink_into_binary_dir(pyi_builder, monkeypatch, tmp_path):
    binaries = []

    # + binary_dir: (1)
    #    - binary.dylib (2)
    # - link_to_binary.dylib -> binary_dir/binary.dylib (3)
    src_path = tmp_path / 'binary_dir' / 'binary.dylib'
    _create_test_binary(src_path)
    binaries.append((src_path, 'binary_dir'))

    src_path = tmp_path / 'link_to_binary.dylib'
    src_path.symlink_to('binary_dir/binary.dylib')
    binaries.append((src_path, '.'))

    bundle_path = _create_app_bundle(pyi_builder, monkeypatch, tmp_path, binaries=binaries)

    # (1) The whole binary directory is placed into `Contents/Frameworks`...
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'binary_dir'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    # ... and symlinked (at directory level) into Contents/Resources.
    check_path = bundle_path / 'Contents' / 'Resources' / 'binary_dir'
    assert check_path.is_dir()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == '../Frameworks/binary_dir'

    # (2) The binary file is placed into directory in `Contents/Frameworks`...
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'binary_dir' / 'binary.dylib'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    # ... but it is also reachable from `Resources/Frameworks`. The linking is done at the parent directory level,
    # so the file itself is NOT seen as a symlink.
    check_path = bundle_path / 'Contents' / 'Resources' / 'binary_dir' / 'binary.dylib'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    # (3) The symlink is replicated in both `Contents/Frameworks` and `Contents/Resources`, and points to the resource
    # (file or symlink) in the same directory.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'link_to_binary.dylib'
    assert check_path.is_file()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == 'binary_dir/binary.dylib'

    check_path = bundle_path / 'Contents' / 'Resources' / 'link_to_binary.dylib'
    assert check_path.is_file()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == 'binary_dir/binary.dylib'


# Test with symlinks in top-level directory pointing to files in mixed-content directory.
@pytest.mark.darwin
@onedir_only
def test_macos_bundle_layout_symlink_into_mixed_dir(pyi_builder, monkeypatch, tmp_path):
    datas = []
    binaries = []

    # + mixed_dir: (1)
    #    - data_file.txt (2)
    #    - binary.dylib (3)
    # - link_to_data_file.txt -> mixed_dir/data_file.txt (4)
    # - link_to_binary.dylib -> mixed_dir/link_to_binary.dylib (5)
    src_path = tmp_path / 'mixed_dir' / 'data_file.txt'
    _create_test_data_file(src_path)
    datas.append((src_path, 'mixed_dir'))

    src_path = tmp_path / 'mixed_dir' / 'binary.dylib'
    _create_test_binary(src_path)
    binaries.append((src_path, 'mixed_dir'))

    src_path = tmp_path / 'link_to_data_file.txt'
    src_path.symlink_to('mixed_dir/data_file.txt')
    datas.append((src_path, '.'))

    src_path = tmp_path / 'link_to_binary.dylib'
    src_path.symlink_to('mixed_dir/binary.dylib')
    binaries.append((src_path, '.'))

    bundle_path = _create_app_bundle(pyi_builder, monkeypatch, tmp_path, datas=datas, binaries=binaries)

    # (1) The mixed-content directory is created in both `Contents/Frameworks` and `Contents/Resources` (i.e., no
    # linking at the directory level).
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'mixed_dir'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    check_path = bundle_path / 'Contents' / 'Resources' / 'mixed_dir'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    # (2) The data file is placed into directory in `Contents/Resources`...
    check_path = bundle_path / 'Contents' / 'Resources' / 'mixed_dir' / 'data_file.txt'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    # ... and symlinked into directory in `Contents/Frameworks`.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'mixed_dir' / 'data_file.txt'
    assert check_path.is_file()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == '../../Resources/mixed_dir/data_file.txt'

    # (3) The binary is placed into directory in `Contents/Frameworks`...
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'mixed_dir' / 'binary.dylib'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    # ... and symlinked into directory in `Contents/Resources`.
    check_path = bundle_path / 'Contents' / 'Resources' / 'mixed_dir' / 'binary.dylib'
    assert check_path.is_file()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == '../../Frameworks/mixed_dir/binary.dylib'

    # (4) The symlink is replicated in both `Contents/Frameworks` and `Contents/Resources`, and points to the resource
    # (file or symlink) in the same directory.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'link_to_data_file.txt'
    assert check_path.is_file()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == 'mixed_dir/data_file.txt'

    check_path = bundle_path / 'Contents' / 'Resources' / 'link_to_data_file.txt'
    assert check_path.is_file()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == 'mixed_dir/data_file.txt'

    # (5) The symlink is replicated in both `Contents/Frameworks` and `Contents/Resources`, and points to the resource
    # (file or symlink) in the same directory.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'link_to_binary.dylib'
    assert check_path.is_file()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == 'mixed_dir/binary.dylib'

    check_path = bundle_path / 'Contents' / 'Resources' / 'link_to_binary.dylib'
    assert check_path.is_file()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == 'mixed_dir/binary.dylib'


# Test with .framework bundle in top-level directory and framework's binary symlinked to top-level directory.
# This implicitly also tests that we do not replace the dot in the .framework bundle's directory name (the .framework
# bundle directories are the only directories in `Contents/Frameworks` that are allowed to have a dot in name).
@pytest.mark.darwin
@onedir_only
def test_macos_bundle_layout_framework_in_top_level(pyi_builder, monkeypatch, tmp_path):
    datas = []
    binaries = []

    # + Dummy.framework: (1)
    #    + Versions: (2)
    #       + A: (3)
    #          - Dummy (4)
    #          + Resources: (5)
    #             - Info.plist (6)
    # - Dummy -> Dummy.framework/Versions/A/Dummy (7)

    src_path = tmp_path / 'Dummy.framework'
    _create_test_framework(src_path)
    binaries.append((src_path / 'Versions' / 'A' / 'Dummy', 'Dummy.framework/Versions/A'))
    # NOTE1: Info.plist should be collected automatically based on the collected framework binary.
    # NOTE2: symlink `Current` -> `A` should be automatically generated in `Dummy.framework/Versions`.

    src_path = tmp_path / 'Dummy'
    src_path.symlink_to('Dummy.framework/Versions/A/Dummy')
    binaries.append((src_path, '.'))

    bundle_path = _create_app_bundle(pyi_builder, monkeypatch, tmp_path, datas=datas, binaries=binaries)

    # (1) The .framework directory is placed into `Contents/Frameworks`...
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'Dummy.framework'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    # ... and symlinked (at directory level) into Contents/Resources.
    check_path = bundle_path / 'Contents' / 'Resources' / 'Dummy.framework'
    assert check_path.is_dir()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == '../Frameworks/Dummy.framework'

    # (2) The content of .framework are placed into directory in `Contents/Frameworks`...
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'Dummy.framework' / 'Versions'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    # ... but are also reachable from `Resources/Frameworks`. The linking is done at the parent directory level, so the
    # files/directories themselves are NOT seen as symlinks.
    check_path = bundle_path / 'Contents' / 'Resources' / 'Dummy.framework' / 'Versions'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    # (3) Same for `Versions/<version>` directory.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'Dummy.framework' / 'Versions' / 'A'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    check_path = bundle_path / 'Contents' / 'Resources' / 'Dummy.framework' / 'Versions' / 'A'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    # (4) Same for binary within the `<version>` directory.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'Dummy.framework' / 'Versions' / 'A' / 'Dummy'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    check_path = bundle_path / 'Contents' / 'Resources' / 'Dummy.framework' / 'Versions' / 'A' / 'Dummy'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    # (5) Same for `Resources` directory within the `<version>` directory.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'Dummy.framework' / 'Versions' / 'A' / 'Resources'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    check_path = bundle_path / 'Contents' / 'Resources' / 'Dummy.framework' / 'Versions' / 'A' / 'Resources'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    # (6) Same for `Info.plist` in `Resources` directory.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'Dummy.framework' / 'Versions' / 'A' / 'Resources' / \
        'Info.plist'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    check_path = bundle_path / 'Contents' / 'Resources' / 'Dummy.framework' / 'Versions' / 'A' / 'Resources' / \
        'Info.plist'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    # (X) A symlink `Current` pointing to `<version>` should be automatically created inside `Versions` directory.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'Dummy.framework' / 'Versions' / 'Current'
    assert check_path.is_dir()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == 'A'

    check_path = bundle_path / 'Contents' / 'Resources' / 'Dummy.framework' / 'Versions' / 'Current'
    assert check_path.is_dir()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == 'A'

    # (7) The symlink is replicated in both `Contents/Frameworks` and `Contents/Resources`, and points to the resource
    # (file or symlink) in the same directory.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'Dummy'
    assert check_path.is_file()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == 'Dummy.framework/Versions/A/Dummy'

    check_path = bundle_path / 'Contents' / 'Resources' / 'Dummy'
    assert check_path.is_file()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == 'Dummy.framework/Versions/A/Dummy'


# Test with .framework bundle in binary-only directory and framework's binary symlinked to top-level directory.
@pytest.mark.darwin
@onedir_only
def test_macos_bundle_layout_framework_in_binary_dir(pyi_builder, monkeypatch, tmp_path):
    datas = []
    binaries = []

    # + binary_dir: (1)
    #    - binary.dylib (2)
    #    + Dummy.framework: (3)
    #       + Versions: (4)
    #          + A: (5)
    #             - Dummy (6)
    #             + Resources: (7)
    #                - Info.plist (8)
    # - Dummy -> binary_dir/Dummy.framework/Versions/A/Dummy (9)

    src_path = tmp_path / 'binary_dir' / 'binary.dylib'
    _create_test_binary(src_path)
    binaries.append((src_path, 'binary_dir'))

    src_path = tmp_path / 'binary_dir' / 'Dummy.framework'
    _create_test_framework(src_path)
    binaries.append((src_path / 'Versions' / 'A' / 'Dummy', 'binary_dir/Dummy.framework/Versions/A'))
    # NOTE1: Info.plist should be collected automatically based on the collected framework binary.
    # NOTE2: symlink `Current` -> `A` should be automatically generated in `Dummy.framework/Versions`.

    src_path = tmp_path / 'Dummy'
    src_path.symlink_to('binary_dir/Dummy.framework/Versions/A/Dummy')
    binaries.append((src_path, '.'))

    bundle_path = _create_app_bundle(pyi_builder, monkeypatch, tmp_path, datas=datas, binaries=binaries)

    # (1) The whole binary directory is placed into `Contents/Frameworks`...
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'binary_dir'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    # ... and symlinked (at directory level) into Contents/Resources.
    check_path = bundle_path / 'Contents' / 'Resources' / 'binary_dir'
    assert check_path.is_dir()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == '../Frameworks/binary_dir'

    # (2) The binary file is placed into directory in `Contents/Frameworks`...
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'binary_dir' / 'binary.dylib'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    # ... but it is also reachable from `Resources/Frameworks`. The linking is done at the parent directory level,
    # so the file itself is NOT seen as a symlink.
    check_path = bundle_path / 'Contents' / 'Resources' / 'binary_dir' / 'binary.dylib'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    # (3) The same applies to the .framework directory.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'binary_dir' / 'Dummy.framework'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    check_path = bundle_path / 'Contents' / 'Resources' / 'binary_dir' / 'Dummy.framework'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    # (4) Same for `Versions` directory inside .framework directory.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'binary_dir' / 'Dummy.framework' / 'Versions'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    check_path = bundle_path / 'Contents' / 'Resources' / 'binary_dir' / 'Dummy.framework' / 'Versions'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    # (5) Same for `Versions/<version>` directory.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'binary_dir' / 'Dummy.framework' / 'Versions' / 'A'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    check_path = bundle_path / 'Contents' / 'Resources' / 'binary_dir' / 'Dummy.framework' / 'Versions' / 'A'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    # (6) Same for binary within the `<version>` directory.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'binary_dir' / 'Dummy.framework' / 'Versions' / 'A' / 'Dummy'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    check_path = bundle_path / 'Contents' / 'Resources' / 'binary_dir' / 'Dummy.framework' / 'Versions' / 'A' / 'Dummy'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    # (7) Same for `Resources` directory within the `<version>` directory.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'binary_dir' / 'Dummy.framework' / 'Versions' / 'A' / \
        'Resources'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    check_path = bundle_path / 'Contents' / 'Resources' / 'binary_dir' / 'Dummy.framework' / 'Versions' / 'A' / \
        'Resources'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    # (8) Same for `Info.plist` in `Resources` directory.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'binary_dir' / 'Dummy.framework' / 'Versions' / 'A' / \
        'Resources' / 'Info.plist'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    check_path = bundle_path / 'Contents' / 'Resources' / 'binary_dir' / 'Dummy.framework' / 'Versions' / 'A' / \
        'Resources' / 'Info.plist'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    # (X) A symlink `Current` pointing to `<version>` should be automatically created inside `Versions` directory.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'binary_dir' / 'Dummy.framework' / 'Versions' / 'Current'
    assert check_path.is_dir()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == 'A'

    check_path = bundle_path / 'Contents' / 'Resources' / 'binary_dir' / 'Dummy.framework' / 'Versions' / 'Current'
    assert check_path.is_dir()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == 'A'

    # (9) The symlink is replicated in both `Contents/Frameworks` and `Contents/Resources`, and points to the resource
    # (file or symlink) in the same directory.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'Dummy'
    assert check_path.is_file()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == 'binary_dir/Dummy.framework/Versions/A/Dummy'

    check_path = bundle_path / 'Contents' / 'Resources' / 'Dummy'
    assert check_path.is_file()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == 'binary_dir/Dummy.framework/Versions/A/Dummy'


# Test with .framework bundle in mixed-content directory and framework's binary symlinked to top-level directory.
# This also tests that a directory is recognized as a mixed-content one if it contains a data file and a .framework
# bundle (i.e., no other binary files).
@pytest.mark.darwin
@onedir_only
def test_macos_bundle_layout_framework_in_mixed_dir(pyi_builder, monkeypatch, tmp_path):
    datas = []
    binaries = []

    # + mixed_dir: (1)
    #    - data_file.txt (2)
    #    + Dummy.framework: (3)
    #       + Versions: (4)
    #          + A: (5)
    #             - Dummy (6)
    #             + Resources: (7)
    #                - Info.plist (8)
    # - Dummy -> mixed_dir/Dummy.framework/Versions/A/Dummy (9)

    src_path = tmp_path / 'mixed_dir' / 'data_file.txt'
    _create_test_data_file(src_path)
    datas.append((src_path, 'mixed_dir'))

    src_path = tmp_path / 'mixed_dir' / 'Dummy.framework'
    _create_test_framework(src_path)
    binaries.append((src_path / 'Versions' / 'A' / 'Dummy', 'mixed_dir/Dummy.framework/Versions/A'))
    # NOTE1: Info.plist should be collected automatically based on the collected framework binary.
    # NOTE2: symlink `Current` -> `A` should be automatically generated in `Dummy.framework/Versions`.

    src_path = tmp_path / 'Dummy'
    src_path.symlink_to('mixed_dir/Dummy.framework/Versions/A/Dummy')
    binaries.append((src_path, '.'))

    bundle_path = _create_app_bundle(pyi_builder, monkeypatch, tmp_path, datas=datas, binaries=binaries)

    # (1) The mixed-content directory is created in both `Contents/Frameworks` and `Contents/Resources` (i.e., no
    # linking at the directory level).
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'mixed_dir'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    check_path = bundle_path / 'Contents' / 'Resources' / 'mixed_dir'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    # (2) The data file is placed into directory in `Contents/Resources`...
    check_path = bundle_path / 'Contents' / 'Resources' / 'mixed_dir' / 'data_file.txt'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    # ... and symlinked into directory in `Contents/Frameworks`.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'mixed_dir' / 'data_file.txt'
    assert check_path.is_file()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == '../../Resources/mixed_dir/data_file.txt'

    # (3) The .framework bundle directory is placed into directory in `Contents/Frameworks`...
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'mixed_dir' / 'Dummy.framework'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    # ... and symlinked into `Resources/Frameworks`.
    check_path = bundle_path / 'Contents' / 'Resources' / 'mixed_dir' / 'Dummy.framework'
    assert check_path.is_dir()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == '../../Frameworks/mixed_dir/Dummy.framework'

    # (4) The contents inside the .framework directory is reachable from both directories, and due to symlinking at
    # parent (= .framework) directory, they are not visible as symlinks themselves. In this case, this applies to the
    # `Versions` directory inside .framework directory.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'mixed_dir' / 'Dummy.framework' / 'Versions'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    check_path = bundle_path / 'Contents' / 'Resources' / 'mixed_dir' / 'Dummy.framework' / 'Versions'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    # (5) Same for `Versions/<version>` directory.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'mixed_dir' / 'Dummy.framework' / 'Versions' / 'A'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    check_path = bundle_path / 'Contents' / 'Resources' / 'mixed_dir' / 'Dummy.framework' / 'Versions' / 'A'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    # (6) Same for binary within the `<version>` directory.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'mixed_dir' / 'Dummy.framework' / 'Versions' / 'A' / 'Dummy'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    check_path = bundle_path / 'Contents' / 'Resources' / 'mixed_dir' / 'Dummy.framework' / 'Versions' / 'A' / 'Dummy'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    # (7) Same for `Resources` directory within the `<version>` directory.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'mixed_dir' / 'Dummy.framework' / 'Versions' / 'A' / \
        'Resources'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    check_path = bundle_path / 'Contents' / 'Resources' / 'mixed_dir' / 'Dummy.framework' / 'Versions' / 'A' / \
        'Resources'
    assert check_path.is_dir()
    assert not check_path.is_symlink()

    # (8) Same for `Info.plist` in `Resources` directory.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'mixed_dir' / 'Dummy.framework' / 'Versions' / 'A' / \
        'Resources' / 'Info.plist'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    check_path = bundle_path / 'Contents' / 'Resources' / 'mixed_dir' / 'Dummy.framework' / 'Versions' / 'A' / \
        'Resources' / 'Info.plist'
    assert check_path.is_file()
    assert not check_path.is_symlink()

    # (X) A symlink `Current` pointing to `<version>` should be automatically created inside `Versions` directory.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'mixed_dir' / 'Dummy.framework' / 'Versions' / 'Current'
    assert check_path.is_dir()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == 'A'

    check_path = bundle_path / 'Contents' / 'Resources' / 'mixed_dir' / 'Dummy.framework' / 'Versions' / 'Current'
    assert check_path.is_dir()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == 'A'

    # (9) The symlink is replicated in both `Contents/Frameworks` and `Contents/Resources`, and points to the resource
    # (file or symlink) in the same directory.
    check_path = bundle_path / 'Contents' / 'Frameworks' / 'Dummy'
    assert check_path.is_file()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == 'mixed_dir/Dummy.framework/Versions/A/Dummy'

    check_path = bundle_path / 'Contents' / 'Resources' / 'Dummy'
    assert check_path.is_file()
    assert check_path.is_symlink()
    assert os.readlink(check_path) == 'mixed_dir/Dummy.framework/Versions/A/Dummy'
