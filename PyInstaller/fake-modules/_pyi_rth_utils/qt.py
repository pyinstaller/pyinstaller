# -----------------------------------------------------------------------------
# Copyright (c) 2024, PyInstaller Development Team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: Apache-2.0
# -----------------------------------------------------------------------------

import os
import importlib
import atexit

# Helper for ensuring that only one Qt bindings package is registered at run-time via run-time hooks.
_registered_qt_bindings = None


def ensure_single_qt_bindings_package(qt_bindings):
    global _registered_qt_bindings
    if _registered_qt_bindings is not None:
        raise RuntimeError(
            f"Cannot execute run-time hook for {qt_bindings!r} because run-time hook for {_registered_qt_bindings!r} "
            "has been run before, and PyInstaller-frozen applications do not support multiple Qt bindings in the same "
            "application!"
        )
    _registered_qt_bindings = qt_bindings


# Helper for relocating Qt prefix via embedded qt.conf file.
_QT_CONF_FILENAME = ":/qt/etc/qt.conf"

_QT_CONF_RESOURCE_NAME = (
    # qt
    b"\x00\x02"
    b"\x00\x00\x07\x84"
    b"\x00\x71"
    b"\x00\x74"
    # etc
    b"\x00\x03"
    b"\x00\x00\x6c\xa3"
    b"\x00\x65"
    b"\x00\x74\x00\x63"
    # qt.conf
    b"\x00\x07"
    b"\x08\x74\xa6\xa6"
    b"\x00\x71"
    b"\x00\x74\x00\x2e\x00\x63\x00\x6f\x00\x6e\x00\x66"
)

_QT_CONF_RESOURCE_STRUCT = (
    # :
    b"\x00\x00\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x01"
    # :/qt
    b"\x00\x00\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x02"
    # :/qt/etc
    b"\x00\x00\x00\x0a\x00\x02\x00\x00\x00\x01\x00\x00\x00\x03"
    # :/qt/etc/qt.conf
    b"\x00\x00\x00\x16\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00"
)


def create_embedded_qt_conf(qt_bindings, prefix_path):
    # The QtCore module might be unavailable if we collected just the top-level binding package (e.g., PyQt5) without
    # any of its submodules. Since this helper is called from run-time hook for the binding package, we need to handle
    # that scenario here.
    try:
        QtCore = importlib.import_module(qt_bindings + ".QtCore")
    except ImportError:
        return

    # No-op if embedded qt.conf already exists
    if QtCore.QFile.exists(_QT_CONF_FILENAME):
        return

    # Create qt.conf file that relocates Qt prefix.
    # NOTE: paths should use POSIX-style forward slashes as separator, even on Windows.
    if os.sep == '\\':
        prefix_path = prefix_path.replace(os.sep, '/')

    qt_conf = f"[Paths]\nPrefix = {prefix_path}\n"
    if os.name == 'nt' and qt_bindings in {"PySide2", "PySide6"}:
        # PySide PyPI wheels on Windows set LibraryExecutablesPath to PrefixPath
        qt_conf += f"LibraryExecutables = {prefix_path}"

    # Encode the contents; in Qt5, QSettings uses Latin1 encoding, in Qt6, it uses UTF8.
    if qt_bindings in {"PySide2", "PyQt5"}:
        qt_conf = qt_conf.encode("latin1")
    else:
        qt_conf = qt_conf.encode("utf-8")

    # Prepend data size (32-bit integer, big endian)
    qt_conf_size = len(qt_conf)
    qt_resource_data = qt_conf_size.to_bytes(4, 'big') + qt_conf

    # Register
    succeeded = QtCore.qRegisterResourceData(
        0x01,
        _QT_CONF_RESOURCE_STRUCT,
        _QT_CONF_RESOURCE_NAME,
        qt_resource_data,
    )
    if not succeeded:
        return  # Tough luck

    # Unregister the resource at exit, to ensure that the registered resource on Qt/C++ side does not outlive the
    # `_qt_resource_data` python variable and its data buffer. This also adds a reference to the `_qt_resource_data`,
    # which conveniently ensures that the data is not garbage collected before we perform the cleanup (otherwise garbage
    # collector might kick in at any time after we exit this helper function, and `qRegisterResourceData` does not seem
    # to make a copy of the data!).
    atexit.register(
        QtCore.qUnregisterResourceData,
        0x01,
        _QT_CONF_RESOURCE_STRUCT,
        _QT_CONF_RESOURCE_NAME,
        qt_resource_data,
    )
