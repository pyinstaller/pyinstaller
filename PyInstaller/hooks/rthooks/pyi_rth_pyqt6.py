#-----------------------------------------------------------------------------
# Copyright (c) 2021-2023, PyInstaller Development Team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: Apache-2.0
#-----------------------------------------------------------------------------

# The path to Qt's components may not default to the wheel layout for self-compiled PyQt6 installations. Mandate the
# wheel layout. See ``utils/hooks/qt.py`` for more details.


def _pyi_rthook():
    import os
    import sys

    from _pyi_rth_utils import is_macos_app_bundle, prepend_path_to_environment_variable
    from _pyi_rth_utils import qt as qt_rth_utils

    # Ensure this is the only Qt bindings package in the application.
    qt_rth_utils.ensure_single_qt_bindings_package("PyQt6")

    # Try PyQt6 6.0.3-style path first...
    pyqt_path = os.path.join(sys._MEIPASS, 'PyQt6', 'Qt6')
    if not os.path.isdir(pyqt_path):
        # ... and fall back to the older version.
        pyqt_path = os.path.join(sys._MEIPASS, 'PyQt6', 'Qt')

    os.environ['QT_PLUGIN_PATH'] = os.path.join(pyqt_path, 'plugins')

    if is_macos_app_bundle:
        # Special handling for macOS .app bundles. To satisfy codesign requirements, we are forced to split `qml`
        # directory into two parts; one that keeps only binaries (rooted in `Contents/Frameworks`) and one that keeps
        # only data files (rooted in `Contents/Resources), with files from one directory tree being symlinked to the
        # other to maintain illusion of a single mixed-content directory. As Qt seems to compute the identifier of its
        # QML components based on location of the `qmldir` file w.r.t. the registered QML import paths, we need to
        # register both paths, because the `qmldir` file for a component could be reached via either directory tree.
        pyqt_path_res = os.path.normpath(
            os.path.join(sys._MEIPASS, '..', 'Resources', os.path.relpath(pyqt_path, sys._MEIPASS))
        )
        os.environ['QML2_IMPORT_PATH'] = os.pathsep.join([
            os.path.join(pyqt_path_res, 'qml'),
            os.path.join(pyqt_path, 'qml'),
        ])
    else:
        os.environ['QML2_IMPORT_PATH'] = os.path.join(pyqt_path, 'qml')

    # Add `sys._MEIPASS` to `PATH` in order to ensure that `QtNetwork` can discover OpenSSL DLLs that might have been
    # collected there (i.e., when they were not shipped with the package, and were collected from an external location).
    if sys.platform.startswith('win'):
        prepend_path_to_environment_variable(sys._MEIPASS, 'PATH')

    # For macOS POSIX builds, we need to add `sys._MEIPASS` to `DYLD_LIBRARY_PATH` so that QtNetwork can discover
    # OpenSSL dynamic libraries for its `openssl` TLS backend. This also prevents fallback to external locations, such
    # as Homebrew. For .app bundles, this is unnecessary because `QtNetwork` explicitly searches `Contents/Frameworks`.
    if sys.platform == 'darwin' and not is_macos_app_bundle:
        prepend_path_to_environment_variable(sys._MEIPASS, 'DYLD_LIBRARY_PATH')

    # Qt bindings package installed via PyPI wheels typically ensures that its bundled Qt is relocatable, by creating
    # embedded `qt.conf` file during its initialization. This run-time generated qt.conf dynamically sets the Qt prefix
    # path to the package's Qt directory. For bindings packages that do not create embedded `qt.conf` during their
    # initialization (for example, conda-installed packages), try to perform this step ourselves.
    qt_rth_utils.create_embedded_qt_conf("PyQt6", pyqt_path)


_pyi_rthook()
del _pyi_rthook
