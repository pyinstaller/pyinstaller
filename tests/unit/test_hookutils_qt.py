#-----------------------------------------------------------------------------
# Copyright (c) 2026, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import logging
import os
import pathlib

import pytest

from PyInstaller import compat
from PyInstaller.depend import bindepend
from PyInstaller.utils.hooks.qt import QtLibraryInfo


def _openssl3_dll_names():
    """OpenSSL 3.x shared library names as searched for by the Windows QtNetwork collection code."""
    machine_suffix = '-x64' if compat.is_64bits else ''
    return (f'libssl-3{machine_suffix}.dll', f'libcrypto-3{machine_suffix}.dll')


@pytest.fixture
def qt_library_info(tmp_path):
    """
    A PySide6 `QtLibraryInfo` instance with manually provided location information, so no Qt introspection (and
    therefore no PySide6 installation) is required.
    """
    info = QtLibraryInfo('PySide6')
    # Setting `version` marks the instance as initialized and prevents the lazy Qt introspection from ever being
    # triggered when the code under test accesses instance attributes.
    info.version = (6, 7, 0)
    info.package_location = pathlib.Path(tmp_path / 'site-packages' / 'PySide6').resolve()
    info.qt_lib_dir = pathlib.Path(info.package_location / 'Qt' / 'bin').resolve()
    info.qt_lib_dir.mkdir(parents=True)
    return info


@pytest.fixture
def fake_library_resolution(monkeypatch, tmp_path):
    """
    Replace `bindepend` library resolution with a plain filesystem-based search that (unlike the real Windows
    implementation) does not perform any PE architecture checks. The `PATH` environment variable is redirected to an
    empty directory under `tmp_path`, and `compat.base_prefix` to an empty directory under `tmp_path`, so that tests
    control all locations involved in the resolution.
    """
    # Directories whose contents are set up by individual tests.
    dirs = {
        'path': tmp_path / 'build-machine' / 'somewhere-on-path',
        'python_dlls': tmp_path / 'build-python' / 'DLLs',
        'python_base': tmp_path / 'build-python',
    }
    for directory in dirs.values():
        directory.mkdir(parents=True, exist_ok=True)

    def _resolve_in_search_paths(name, search_paths=None):
        for search_path in search_paths or []:
            fullpath = os.path.join(search_path, name)
            if os.path.isfile(fullpath):
                return os.path.normpath(fullpath)
        return None

    def _resolve_library_path(name, search_paths=None):
        # Emulate the Windows search order of `bindepend.resolve_library_path`: caller-supplied search paths first,
        # followed by directories from the PATH environment variable.
        fullpath = _resolve_in_search_paths(name, search_paths)
        if fullpath is not None:
            return fullpath
        path_dirs = [path for path in os.environ.get('PATH', '').split(os.pathsep) if path]
        return _resolve_in_search_paths(name, path_dirs)

    monkeypatch.setattr(bindepend, '_resolve_library_path_in_search_paths', _resolve_in_search_paths)
    monkeypatch.setattr(bindepend, 'resolve_library_path', _resolve_library_path)
    monkeypatch.setenv('PATH', str(dirs['path']))
    monkeypatch.setattr(compat, 'base_prefix', str(dirs['python_base']))

    return dirs


def _create_dlls(directory, names):
    for name in names:
        (directory / name).touch()


def test_qtnetwork_openssl_dlls_collected_from_qt_directory_without_warning(
    qt_library_info, fake_library_resolution, caplog
):
    """
    OpenSSL DLLs located in the Qt shared library directory (e.g., shipped by conda or msys2 Qt packages, or by PyQt5
    PyPI wheels) are collected from there, without any warning.
    """
    dll_names = _openssl3_dll_names()
    _create_dlls(qt_library_info.qt_lib_dir, dll_names)

    with caplog.at_level(logging.WARNING, logger='PyInstaller.utils.hooks.qt'):
        binaries = qt_library_info._collect_qtnetwork_openssl_windows(0x300000F0)

    # DLLs located inside the bindings' python package are collected with their directory layout preserved.
    dst_dir = qt_library_info.qt_lib_dir.relative_to(qt_library_info.package_location.parent)
    assert binaries == [(str(qt_library_info.qt_lib_dir / name), str(dst_dir)) for name in dll_names]
    assert caplog.records == []


def test_qtnetwork_openssl_dlls_prefer_python_provided_over_path(qt_library_info, fake_library_resolution, caplog):
    """
    OpenSSL DLLs provided by the build python ({sys.base_prefix}/DLLs) take precedence over copies found via PATH
    search, and their collection is silent. This pins the collected DLL set to a known-compatible source regardless
    of the contents of the build machine's PATH.
    """
    dll_names = _openssl3_dll_names()
    _create_dlls(fake_library_resolution['python_dlls'], dll_names)
    _create_dlls(fake_library_resolution['path'], dll_names)  # decoy copies on PATH

    with caplog.at_level(logging.WARNING, logger='PyInstaller.utils.hooks.qt'):
        binaries = qt_library_info._collect_qtnetwork_openssl_windows(0x300000F0)

    assert binaries == [(str(fake_library_resolution['python_dlls'] / name), '.') for name in dll_names]
    assert caplog.records == []


def test_qtnetwork_openssl_dlls_from_path_fallback_emit_warning(qt_library_info, fake_library_resolution, caplog):
    """
    When OpenSSL DLLs cannot be found in any pinned location and are instead picked up from the build machine's PATH,
    each collected DLL is accompanied by a build-time warning that names both the DLL and its source directory.
    """
    dll_names = _openssl3_dll_names()
    _create_dlls(fake_library_resolution['path'], dll_names)

    with caplog.at_level(logging.WARNING, logger='PyInstaller.utils.hooks.qt'):
        binaries = qt_library_info._collect_qtnetwork_openssl_windows(0x300000F0)

    assert binaries == [(str(fake_library_resolution['path'] / name), '.') for name in dll_names]
    messages = [record.getMessage() for record in caplog.records]
    for name in dll_names:
        matching = [message for message in messages if name in message]
        assert len(matching) == 1  # exactly one warning per collected DLL
        # The source path is embedded via %r formatting; use repr() to account for platform-specific escaping.
        assert repr(str(fake_library_resolution['path'] / name)) in matching[0]
        assert 'PATH' in matching[0]


def test_qtnetwork_openssl_dlls_unavailable(qt_library_info, fake_library_resolution, caplog):
    """No OpenSSL DLLs anywhere; nothing is collected and no warning is emitted."""
    with caplog.at_level(logging.WARNING, logger='PyInstaller.utils.hooks.qt'):
        binaries = qt_library_info._collect_qtnetwork_openssl_windows(0x300000F0)

    assert binaries == []
    assert caplog.records == []
