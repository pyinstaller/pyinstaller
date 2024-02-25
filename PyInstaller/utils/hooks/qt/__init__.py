# ----------------------------------------------------------------------------
# Copyright (c) 2005-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import glob
import os
import pathlib
import re

from PyInstaller import compat
from PyInstaller import isolated
from PyInstaller import log as logging
from PyInstaller.depend import bindepend
from PyInstaller.utils import hooks, misc
from PyInstaller.utils.hooks.qt import _modules_info

logger = logging.getLogger(__name__)

# Qt deployment approach
# ----------------------
# This is the core of PyInstaller's approach to Qt deployment. It is based on:
#
# - Discovering the location of Qt libraries by introspection, using QtLibraryInfo_. This provides compatibility with
#   many variants of Qt5/6 (conda, self-compiled, provided by a Linux distro, etc.) and many versions of Qt5/6, all of
#   which vary in the location of Qt files.
#
# - Placing all frozen PyQt5/6 or PySide2/6 Qt files in a standard subdirectory layout, which matches the layout of the
#   corresponding wheel on PyPI. This is necessary to support Qt installs which are not in a subdirectory of the PyQt5/6
#   or PySide2/6 wrappers. See ``hooks/rthooks/pyi_rth_qt5.py`` for the use of environment variables to establish this
#   layout.
#
# - Emitting warnings on missing QML and translation files which some installations do not have.
#
# - Determining additional files needed for deployment based on the information in the centralized Qt module information
#   list in the ``_modules_info`` module. This includes plugins and translation files associated with each Qt python
#   extension module, as well as additional python Qt extension modules.
#
# - Collecting additional files that are specific to each module and are handled separately, for example:
#
#    - For dynamic OpenGL applications, the ``libEGL.dll``, ``libGLESv2.dll``, ``d3dcompiler_XX.dll`` (the XX is a
#      version number), and ``opengl32sw.dll`` libraries need to be collected on Windows. This is handled by the
#      "base" bindings hook, for example ``hook-PyQt5.py``.
#
#    - If Qt was configured to use ICU, the ``icudtXX.dll``, ``icuinXX.dll``, and ``icuucXX.dll`` libraries need to
#      be collected on Windows. This is handled by the "base" bindings hook, for example ``hook-PyQt5.py``.
#
#    - Per the `Deploying QML Applications <http://doc.qt.io/qt-5/qtquick-deployment.html>`_ page, QML-based
#      applications need the ``qml/`` directory available. This is handled by ``QtQuick`` hook, for example
#      ``hook-PyQt5.QtQuick.py``.
#
#    - For ``QtWebEngine``-based applications, we follow the `deployWebEngineCore
#      <https://code.woboq.org/qt5/qttools/src/windeployqt/main.cpp.html#_ZL19deployWebEngineCoreRK4QMapI7QStringS0_ERK7OptionsbPS0_>`_
#      function copies the following files from ``resources/``, and also copies the web engine process executable.
#       -   ``icudtl.dat``
#       -   ``qtwebengine_devtools_resources.pak``
#       -   ``qtwebengine_resources.pak``
#       -   ``qtwebengine_resources_100p.pak``
#       -   ``qtwebengine_resources_200p.pak``
#
#      This is handled by the ``QtWebEngineCore`` hook, for example  ``hook-PyQt5.QtWebEngineCore.py``.
#
# For details and references, see the `original write-up
# <https://github.com/pyinstaller/pyinstaller/blob/fbf7948be85177dd44b41217e9f039e1d176de6b/PyInstaller/utils/hooks/qt.py#L248-L362>`_
# and the documentation in the ``_modules_info`` module.


# QtModuleInfo
# ------------
# This class contains information about python module (extension), its corresponding Qt module (shared library), and
# associated plugins and translations. It is used within QtLibraryInfo_ to establish name-based mappings for file
# collection.
class QtModuleInfo:
    def __init__(self, module, shared_lib=None, translations=None, plugins=None):
        # Python module (extension) name without package namespace. For example, `QtCore`.
        # Can be None if python bindings do not bind the module, but we still need to establish relationship between
        # the Qt module (shared library) and its plugins and translations.
        self.module = module
        # Associated Qt module (shared library), if any. Used during recursive dependency analysis, where a python
        # module (extension) is analyzed for linked Qt modules (shared libraries), and then their corresponding
        # python modules (extensions) are added to hidden imports. For example, the Qt module name is `Qt5Core` or
        # `Qt6Core`, depending on the Qt version. Can be None for python modules that are not tied to a particular
        # Qt shared library (for example, the corresponding Qt module is headers-only) and hence they cannot be
        # inferred from recursive link-time dependency analysis.
        self.shared_lib = shared_lib
        # List of base names of translation files (if any) associated with the Qt module. Multiple base names may be
        # associated with a single module.
        # For example, `['qt', 'qtbase']` for `QtCore` or `['qtmultimedia']` for `QtMultimedia`.
        self.translations = translations or []
        # List of plugins associated with the Qt module.
        self.plugins = plugins or []

    def __repr__(self):
        return f"(module={self.module!r}, shared_lib={self.shared_lib!r}, " \
               f"translations={self.translations!r}, plugins={self.plugins!r}"


# QtLibraryInfo
# --------------
# This class uses introspection to determine the location of Qt files. This is essential to deal with the many variants
# of the PyQt5/6 and PySide2/6 package, each of which places files in a different location. Therefore, this class
# provides all location-related members of `QLibraryInfo <http://doc.qt.io/qt-5/qlibraryinfo.html>`_.
class QtLibraryInfo:
    def __init__(self, namespace):
        if namespace not in ['PyQt5', 'PyQt6', 'PySide2', 'PySide6']:
            raise Exception('Invalid namespace: {0}'.format(namespace))
        self.namespace = namespace
        # Distinction between PyQt5/6 and PySide2/6
        self.is_pyqt = namespace in {'PyQt5', 'PyQt6'}
        # Distinction between Qt5 and Qt6
        self.qt_major = 6 if namespace in {'PyQt6', 'PySide6'} else 5
        # Determine relative path where Qt libraries and data need to be collected in the frozen application. This
        # varies between PyQt5/PyQt6/PySide2/PySide6, their versions, and platforms. NOTE: it is tempting to consider
        # deriving this path as simply the value of QLibraryInfo.PrefixPath, taken relative to the package's root
        # directory. However, we also need to support non-wheel deployments (e.g., with Qt installed in custom path on
        # Windows, or with Qt and PyQt5 installed on linux using native package manager), and in those, the Qt
        # PrefixPath does not reflect the required relative target path for the frozen application.
        if namespace == 'PyQt5':
            if self._use_new_layout("PyQt5", "5.15.4", False):
                self.qt_rel_dir = os.path.join('PyQt5', 'Qt5')
            else:
                self.qt_rel_dir = os.path.join('PyQt5', 'Qt')
        elif namespace == 'PyQt6':
            if self._use_new_layout("PyQt6", "6.0.3", True):
                self.qt_rel_dir = os.path.join('PyQt6', 'Qt6')
            else:
                self.qt_rel_dir = os.path.join('PyQt6', 'Qt')
        elif namespace == 'PySide2':
            # PySide2 uses PySide2/Qt on linux and macOS, and PySide2 on Windows
            if compat.is_win:
                self.qt_rel_dir = 'PySide2'
            else:
                self.qt_rel_dir = os.path.join('PySide2', 'Qt')
        else:
            # PySide6 follows the same logic as PySide2
            if compat.is_win:
                self.qt_rel_dir = 'PySide6'
            else:
                self.qt_rel_dir = os.path.join('PySide6', 'Qt')

        # Process module information list to construct python-module-name -> info and shared-lib-name -> info mappings.
        self._load_module_info()

    def __repr__(self):
        return f"QtLibraryInfo({self.namespace})"

    # Delay initialization of the Qt library information until the corresponding attributes are first requested.
    def __getattr__(self, name):
        if 'version' in self.__dict__:
            # Initialization was already done, but requested attribute is not available.
            raise AttributeError(name)

        # Load Qt library info...
        self._load_qt_info()
        # ... and return the requested attribute
        return getattr(self, name)

    # Check whether we must use the new layout (e.g. PyQt5/Qt5, PyQt6/Qt6) instead of the old layout (PyQt5/Qt,
    # PyQt6/Qt).
    @staticmethod
    def _use_new_layout(package_basename: str, version: str, fallback_value: bool) -> bool:
        # The PyQt wheels come in both non-commercial and commercial variants. So we need to check if a particular
        # variant is installed before testing its version.
        if hooks.check_requirement(package_basename):
            return hooks.check_requirement(f"{package_basename} >= {version}")
        if hooks.check_requirement(f"{package_basename}_commercial"):
            return hooks.check_requirement(f"{package_basename}_commercial >= {version}")
        return fallback_value

    # Load Qt information (called on first access to related fields)
    def _load_qt_info(self):
        """
        Load and process Qt library information. Called on the first access to the related attributes of the class
        (e.g., `version` or `location`).
        """

        # Ensure self.version exists, even if PyQt{5,6}/PySide{2,6} cannot be imported. Hooks and util functions use
        # `if .version` to check whether package was imported and other attributes are expected to be available.
        # This also serves as a marker that initialization was already done.
        self.version = None

        # Get library path information from Qt. See QLibraryInfo_.
        @isolated.decorate
        def _read_qt_library_info(package):
            import os
            import sys
            import importlib

            # Import the Qt-based package
            # equivalent to: from package.QtCore import QLibraryInfo, QCoreApplication
            QtCore = importlib.import_module('.QtCore', package)
            QLibraryInfo = QtCore.QLibraryInfo
            QCoreApplication = QtCore.QCoreApplication

            # QLibraryInfo is not always valid until a QCoreApplication is instantiated.
            app = QCoreApplication(sys.argv)  # noqa: F841

            # Qt6 deprecated QLibraryInfo.location() in favor of QLibraryInfo.path(), and
            # QLibraryInfo.LibraryLocation enum was replaced by QLibraryInfo.LibraryPath.
            if hasattr(QLibraryInfo, 'path'):
                # Qt6; enumerate path enum values directly from the QLibraryInfo.LibraryPath enum.
                path_names = [x for x in dir(QLibraryInfo.LibraryPath) if x.endswith('Path')]
                location = {x: QLibraryInfo.path(getattr(QLibraryInfo.LibraryPath, x)) for x in path_names}
            else:
                # Qt5; in recent versions, location enum values can be enumeratd from QLibraryInfo.LibraryLocation.
                # However, in older versions of Qt5 and its python bindings, that is unavailable. Hence the
                # enumeration of "*Path"-named members of QLibraryInfo.
                path_names = [x for x in dir(QLibraryInfo) if x.endswith('Path')]
                location = {x: QLibraryInfo.location(getattr(QLibraryInfo, x)) for x in path_names}

            # Determine the python-based package location, by looking where the QtCore module is located.
            package_location = os.path.dirname(QtCore.__file__)

            # Determine Qt version. Works for Qt 5.8 and later, where QLibraryInfo.version() was introduced.
            try:
                version = QLibraryInfo.version().segments()
            except AttributeError:
                version = []

            return {
                'is_debug_build': QLibraryInfo.isDebugBuild(),
                'version': version,
                'location': location,
                'package_location': package_location,
            }

        try:
            qt_info = _read_qt_library_info(self.namespace)
        except Exception as e:
            logger.warning("%s: failed to obtain Qt library info: %s", self, e)
            return

        for k, v in qt_info.items():
            setattr(self, k, v)

        # Turn package_location into pathlib.Path(), and fully resolve it.
        self.package_location = pathlib.Path(self.package_location).resolve()

        # Determine if the Qt is bundled with python package itself; this usually means we are dealing with with PyPI
        # wheels.
        resolved_qt_prefix_path = pathlib.Path(self.location['PrefixPath']).resolve()
        self.qt_inside_package = (
            self.package_location == resolved_qt_prefix_path or  # PySide2 and PySide6 Windows PyPI wheels
            self.package_location in resolved_qt_prefix_path.parents
        )

        # Determine directory that contains Qt shared libraries. On non-Windows, this is typically location given by
        # `LibrariesPath`. On Windows, it is usually `BinariesPath`, except for PySide PyPI wheels, where DLLs are
        # placed in top-level `PrefixPath`.
        if compat.is_win:
            if self.qt_inside_package and not self.is_pyqt:
                # Windows PyPI wheel
                qt_lib_dir = self.location['PrefixPath']
            else:
                qt_lib_dir = self.location['BinariesPath']
        else:
            qt_lib_dir = self.location['LibrariesPath']
        self.qt_lib_dir = pathlib.Path(qt_lib_dir).resolve()

    # Module information list loading/processing
    def _load_module_info(self):
        """
        Process the Qt modules info definition list and construct two dictionaries:
         - dictionary that maps Qt python module names to Qt module info entries
         - dictionary that maps shared library names to Qt module info entries
        """

        self.python_modules = dict()
        self.shared_libraries = dict()

        for entry in _modules_info.QT_MODULES_INFO:
            # If entry specifies applicable bindings, check them
            if entry.bindings:
                applicable_bindings = _modules_info.process_namespace_strings(entry.bindings)
                if self.namespace not in applicable_bindings:
                    continue

            # Create a QtModuleInfo entry
            info_entry = QtModuleInfo(
                module=entry.module,
                shared_lib=f"Qt{self.qt_major}{entry.shared_lib}" if entry.shared_lib else None,
                translations=entry.translations,
                plugins=entry.plugins
            )

            # If we have python module (extension) name, create python-module-name -> info mapping.
            if info_entry.module is not None:
                self.python_modules[info_entry.module] = info_entry

            # If we have Qt module (shared library) name, create shared-lib-name -> info mapping.
            if info_entry.shared_lib is not None:
                self.shared_libraries[info_entry.shared_lib.lower()] = info_entry

    def _normalize_shared_library_name(self, filename):
        """
        Normalize a shared library name into common form that we can use for look-ups and comparisons.
        Primarily intended for Qt shared library names.
        """

        # Take base name, remove suffix, and lower case it.
        lib_name = os.path.splitext(os.path.basename(filename))[0].lower()
        # Linux libraries sometimes have a dotted version number -- ``libfoo.so.3``. It is now ''libfoo.so``,
        # but the ``.so`` must also be removed.
        if compat.is_linux and os.path.splitext(lib_name)[1] == '.so':
            lib_name = os.path.splitext(lib_name)[0]
        # Remove the "lib" prefix (Linux, macOS).
        if lib_name.startswith('lib'):
            lib_name = lib_name[3:]
        # macOS: handle different naming schemes. PyPI wheels ship framework-enabled Qt builds, where shared
        # libraries are part of .framework bundles (e.g., ``PyQt5/Qt5/lib/QtCore.framework/Versions/5/QtCore``).
        # In Anaconda (Py)Qt installations, the shared libraries are installed in environment's library directory,
        # and contain versioned extensions, e.g., ``libQt5Core.5.dylib``.
        if compat.is_darwin:
            if lib_name.startswith('qt') and not lib_name.startswith('qt' + str(self.qt_major)):
                # Qt library from a framework bundle (e.g., ``QtCore``); change prefix from ``qt`` to ``qt5`` or
                # ``qt6`` to match names in Windows/Linux.
                lib_name = 'qt' + str(self.qt_major) + lib_name[2:]
            if lib_name.endswith('.' + str(self.qt_major)):
                # Qt library from Anaconda, which originally had versioned extension, e.g., ``libfoo.5.dynlib``.
                # The above processing turned it into ``foo.5``, so we need to remove the last two characters.
                lib_name = lib_name[:-2]

        # Handle cases with QT_LIBINFIX set to '_conda', i.e. conda-forge builds.
        if lib_name.endswith('_conda'):
            lib_name = lib_name[:-6]

        return lib_name

    # Collection
    def collect_module(self, module_name):
        """
        Collect all dependencies (hiddenimports, binaries, datas) for the given Qt python module.

        This function performs recursive analysis of extension module's link-time dependencies, and uses dictionaries
        built by `_load_module_info` to discover associated plugin types, translation file base names, and hidden
        imports that need to be collected.
        """

        # Accumulate all dependencies in a set to avoid duplicates.
        hiddenimports = set()
        translation_base_names = set()
        plugin_types = set()

        # Exit if the requested library cannot be imported.
        # NOTE: self..version can be empty list on older Qt5 versions (#5381).
        if self.version is None:
            return [], [], []

        logger.debug('%s: processing module %s...', self, module_name)

        # Look up the associated Qt module information by python module name.
        # This allows us to collect associated module data directly, even if there is no associated shared library
        # (e.g., header-only Qt module, or statically-built one).
        short_module_name = module_name.split('.', 1)[-1]  # PySide2.QtModule -> QtModule
        if short_module_name in self.python_modules:
            qt_module_info = self.python_modules[short_module_name]

            # NOTE: no need to add a hiddenimport here, because this is the module under consideration.

            # Add plugins
            plugin_types.update(qt_module_info.plugins)

            # Add translation base name(s)
            translation_base_names.update(qt_module_info.translations)

        # Find the actual module extension file.
        module_file = hooks.get_module_file_attribute(module_name)

        # Additional search path for shared library resolution. This is mostly required for library resolution on
        # Windows (Linux and macOS binaries use run paths to find Qt libs).
        qtlib_search_paths = [
            # For PyQt5 and PyQt6 wheels, shared libraries should be in BinariesPath, while for PySide2 and PySide6,
            # they should be in PrefixPath.
            self.location['BinariesPath' if self.is_pyqt else 'PrefixPath'],
        ]

        # Walk through all the link-time dependencies of a dynamically-linked library (``.so``/``.dll``/``.dylib``).
        imported_libraries = bindepend.get_imports(module_file, qtlib_search_paths)
        while imported_libraries:
            imported_lib_name, imported_lib_path = imported_libraries.pop()  # (name, fullpath) tuple

            # Skip unresolved libraries
            if imported_lib_path is None:
                logger.debug("%s: ignoring unresolved library import %r", self, imported_lib_name)
                continue

            # Normalize the shared library name
            lib_name = self._normalize_shared_library_name(imported_lib_path)
            logger.debug(
                '%s: imported library %r, full path %r -> parsed name %r.', self, imported_lib_name, imported_lib_path,
                lib_name
            )

            # PySide2 and PySide6 on linux seem to link all extension modules against libQt5Core, libQt5Network, and
            # libQt5Qml (or their libQt6* equivalents). While the first two are reasonable, the libQt5Qml dependency
            # pulls in whole QtQml module, along with its data and plugins, which in turn pull in several other Qt
            # libraries, greatly inflating the bundle size (see #6447).
            #
            # Similarly, some extension modules (QtWebChannel, QtWebEngine*) seem to be also linked against libQt5Qml,
            # even when the module can be used without having the whole QtQml module collected.
            #
            # Therefore, we explicitly prevent inclusion of QtQml based on the dynamic library dependency, except for
            # QtQml* and QtQuick* modules, whose use directly implies the use of QtQml.
            if lib_name in ("qt5qml", "qt6qml"):
                if not short_module_name.startswith(('QtQml', 'QtQuick')):
                    logger.debug('%s: ignoring imported library %r.', self, lib_name)
                    continue

            # Use the parsed library name to look up associated Qt module information.
            if lib_name in self.shared_libraries:
                logger.debug('%s: collecting Qt module associated with %r.', self, lib_name)

                # Look up associated module info
                qt_module_info = self.shared_libraries[lib_name]

                # If there is a python extension module associated with Qt module, add it to hiddenimports. Since this
                # means that we (most likely) have a hook available for that module, we can avoid analyzing the shared
                # library itself (i.e., stop the recursive analysis), because this will be done by the corresponding
                # hook.
                if qt_module_info.module:
                    if qt_module_info.module == short_module_name:
                        # The one exception is if we are analyzing shared library associated with the input module; in
                        # that case, avoid adding a hidden import and analyze the library's link-time dependencies. We
                        # do not need to worry about plugins and translations for this particular module, because those
                        # have been handled at the beginning of this function.
                        imported_libraries.update(bindepend.get_imports(imported_lib_path, qtlib_search_paths))
                    else:
                        hiddenimports.add(self.namespace + "." + qt_module_info.module)
                    continue

                # Add plugins
                plugin_types.update(qt_module_info.plugins)

                # Add translation base name(s)
                translation_base_names.update(qt_module_info.translations)

                # Analyze the linked shared libraries for its dependencies (recursive analysis).
                imported_libraries.update(bindepend.get_imports(imported_lib_path, qtlib_search_paths))

        # Collect plugin files.
        binaries = []
        for plugin_type in plugin_types:
            binaries += self.collect_plugins(plugin_type)

        # Collect translation files.
        datas = []
        translation_src = self.location['TranslationsPath']
        translation_dst = os.path.join(self.qt_rel_dir, 'translations')

        for translation_base_name in translation_base_names:
            # Not all PyQt5 installations include translations. See
            # https://github.com/pyinstaller/pyinstaller/pull/3229#issuecomment-359479893
            # and
            # https://github.com/pyinstaller/pyinstaller/issues/2857#issuecomment-368744341.
            translation_pattern = os.path.join(translation_src, translation_base_name + '_*.qm')
            translation_files = glob.glob(translation_pattern)
            if translation_files:
                datas += [(translation_file, translation_dst) for translation_file in translation_files]
            else:
                logger.warning(
                    '%s: could not find translations with base name %r! These translations will not be collected.',
                    self, translation_base_name
                )

        # Convert hiddenimports to a list.
        hiddenimports = list(hiddenimports)

        logger.debug(
            '%s: dependencies for %s:\n'
            '  hiddenimports = %r\n'
            '  binaries = %r\n'
            '  datas = %r', self, module_name, hiddenimports, binaries, datas
        )

        return hiddenimports, binaries, datas

    @staticmethod
    def _filter_release_plugins(plugin_files):
        """
        Filter the provided list of Qt plugin files and remove the debug variants, under the assumption that both the
        release version of a plugin (qtplugin.dll) and its debug variant (qtplugind.dll) appear in the list.
        """
        # All basenames for lookup
        plugin_basenames = {os.path.normcase(os.path.basename(f)) for f in plugin_files}
        # Process all given filenames
        release_plugin_files = []
        for plugin_filename in plugin_files:
            plugin_basename = os.path.normcase(os.path.basename(plugin_filename))
            if plugin_basename.endswith('d.dll'):
                # If we can find a variant without trailing 'd' in the plugin list, then the DLL we are dealing with is
                # a debug variant and needs to be excluded.
                release_name = os.path.splitext(plugin_basename)[0][:-1] + '.dll'
                if release_name in plugin_basenames:
                    continue
            release_plugin_files.append(plugin_filename)
        return release_plugin_files

    def collect_plugins(self, plugin_type):
        """
        Collect all plugins of the specified type from the Qt plugin directory.

        Returns list of (src, dst) tuples.
        """
        # Ensure plugin directory exists
        plugin_src_dir = self.location['PluginsPath']
        if not os.path.isdir(plugin_src_dir):
            raise Exception(f"Qt plugin directory '{plugin_src_dir}' does not exist!")

        # Collect all shared lib files in plugin type (sub)directory
        plugin_files = misc.dlls_in_dir(os.path.join(plugin_src_dir, plugin_type))

        # Windows:
        #
        # dlls_in_dir() grabs all files ending with ``*.dll``, ``*.so`` and ``*.dylib`` in a certain directory. On
        # Windows this would grab debug copies of Qt plugins, which then causes PyInstaller to add a dependency on the
        # Debug CRT *in addition* to the release CRT.
        if compat.is_win:
            plugin_files = self._filter_release_plugins(plugin_files)

        logger.debug("%s: found plugin files for plugin type %r: %r", self, plugin_type, plugin_files)

        plugin_dst_dir = os.path.join(self.qt_rel_dir, 'plugins', plugin_type)

        # Exclude plugins with invalid Qt dependencies.
        binaries = []
        for plugin_file in plugin_files:
            valid, reason = self._validate_plugin_dependencies(plugin_file)
            if valid:
                binaries.append((plugin_file, plugin_dst_dir))
            else:
                logger.debug("%s: excluding plugin %r (%r)! Reason: %s", self, plugin_file, plugin_type, reason)
        return binaries

    def _validate_plugin_dependencies(self, plugin_file):
        """
        Validate Qt dependencies of the given Qt plugin file. For the plugin to pass validation, all its Qt dependencies
        must be available (resolvable), and must be resolvable from the default Qt shared library directory (to avoid
        pulling in libraries from unrelated Qt installations that happen to be in search path).
        """

        imported_libraries = bindepend.get_imports(plugin_file, search_paths=[self.qt_lib_dir])
        for imported_lib_name, imported_lib_path in imported_libraries:
            # Parse/normalize the (unresolved) library name, to determine if dependency is a Qt shared library. If not,
            # skip the validation.
            lib_name = self._normalize_shared_library_name(imported_lib_name)
            if not lib_name.startswith(f"qt{self.qt_major}"):
                continue

            if imported_lib_path is None:
                return False, f"Missing Qt dependency {imported_lib_name!r}."

            imported_lib_path = pathlib.Path(imported_lib_path).resolve()
            if self.qt_lib_dir not in imported_lib_path.parents:
                return (
                    False,
                    f"Qt dependency {imported_lib_name!r} ({str(imported_lib_path)!r}) has been resolved outside of "
                    f"the Qt shared library directory ({str(self.qt_lib_dir)!r})."
                )

        return True, None

    def _collect_all_or_none(self, mandatory_dll_patterns, optional_dll_patterns=None):
        """
        Try to find Qt DLLs from the specified mandatory pattern list. If all mandatory patterns resolve to DLLs,
        collect them all, as well as any DLLs from the optional pattern list. If a mandatory pattern fails to resolve
        to a DLL, return an empty list.

        This allows all-or-none collection of particular groups of Qt DLLs that may or may not be available.
        """
        optional_dll_patterns = optional_dll_patterns or []

        # Package parent path; used to preserve the directory structure when DLLs are collected from the python
        # package (e.g., PyPI wheels).
        package_parent_path = self.package_location.parent

        # On Windows, DLLs are typically placed in `location['BinariesPath']`, except for PySide PyPI wheels, where
        # `location['PrefixPath']` is used. This difference is already handled by `qt_lib_dir`, which is also fully
        # resolved.
        dll_path = self.qt_lib_dir

        # Helper for processing single DLL pattern
        def _process_dll_pattern(dll_pattern):
            discovered_dlls = []

            dll_files = dll_path.glob(dll_pattern)
            for dll_file in dll_files:
                if package_parent_path in dll_file.parents:
                    # The DLL is located within python package; preserve the layout
                    dst_dll_dir = dll_file.parent.relative_to(package_parent_path)
                else:
                    # The DLL is not located within python package; collect into top-level directory
                    dst_dll_dir = '.'
                discovered_dlls.append((str(dll_file), str(dst_dll_dir)))

            return discovered_dlls

        # Process mandatory patterns
        collected_dlls = []
        for pattern in mandatory_dll_patterns:
            discovered_dlls = _process_dll_pattern(pattern)
            if not discovered_dlls:
                return []  # Mandatory pattern resulted in no DLLs; abort
            collected_dlls += discovered_dlls

        # Process optional patterns
        for pattern in optional_dll_patterns:
            collected_dlls += _process_dll_pattern(pattern)

        return collected_dlls

    # Collect required Qt binaries, but only if all binaries in a group exist.
    def collect_extra_binaries(self):
        """
        Collect extra binaries/DLLs required by Qt. These include ANGLE DLLs, OpenGL software renderer DLL, and ICU
        DLLs. Applicable only on Windows (on other OSes, empty list is returned).
        """

        binaries = []

        # Applicable only to Windows.
        if not compat.is_win:
            return []

        # OpenGL: EGL/GLES via ANGLE, software OpenGL renderer.
        binaries += self._collect_all_or_none(['libEGL.dll', 'libGLESv2.dll'], ['d3dcompiler_??.dll'])
        binaries += self._collect_all_or_none(['opengl32sw.dll'])

        # Include ICU files, if they exist.
        # See the "Deployment approach" section at the top of this file.
        binaries += self._collect_all_or_none(['icudt??.dll', 'icuin??.dll', 'icuuc??.dll'])

        return binaries

    # Collect additional shared libraries required for SSL support in QtNetwork, if they are available.
    # Primarily applicable to Windows (see issue #3520, #4048).
    def collect_qtnetwork_files(self):
        """
        Collect extra binaries/shared libraries required by the QtNetwork module, such as OpenSSL shared libraries.
        """

        # No-op if requested Qt-based package is not available.
        if self.version is None:
            return []

        # Check if QtNetwork supports SSL and has OpenSSL backend available (Qt >= 6.1).
        # Also query the run-time OpenSSL version, so we know what dynamic libraries we need to search for.
        @isolated.decorate
        def _check_if_openssl_enabled(package):
            import sys
            import importlib

            # Import the Qt-based package
            # equivalent to: from package.QtCore import QCoreApplication
            QtCore = importlib.import_module('.QtCore', package)
            QCoreApplication = QtCore.QCoreApplication
            QLibraryInfo = QtCore.QLibraryInfo
            # equivalent to: from package.QtNetwork import QSslSocket
            QtNetwork = importlib.import_module('.QtNetwork', package)
            QSslSocket = QtNetwork.QSslSocket

            # Instantiate QCoreApplication to suppress warnings
            app = QCoreApplication(sys.argv)  # noqa: F841

            if not QSslSocket.supportsSsl():
                return False, None

            # Query the run-time OpenSSL version
            openssl_version = QSslSocket.sslLibraryVersionNumber()

            # For Qt >= 6.1, check if `openssl` TLS backend is available
            try:
                qt_version = QLibraryInfo.version().segments()
            except AttributeError:
                qt_version = []  # Qt <= 5.8

            if qt_version < [6, 1]:
                return True, openssl_version  # TLS backends not implemented yet

            return ('openssl' in QSslSocket.availableBackends(), openssl_version)

        openssl_enabled, openssl_version = _check_if_openssl_enabled(self.namespace)
        if not openssl_enabled or openssl_version == 0:
            logger.debug("%s: QtNetwork: does not support SSL or does not use OpenSSL.", self)
            return []

        # The actual search is handled in OS-specific ways.
        if compat.is_win:
            return self._collect_qtnetwork_openssl_windows(openssl_version)
        elif compat.is_darwin:
            return self._collect_qtnetwork_openssl_macos(openssl_version)
        elif compat.is_linux:
            return self._collect_qtnetwork_openssl_linux(openssl_version)
        else:
            logger.warning("%s: QtNetwork: collection of OpenSSL not implemented for this platform!")
            return []

    def _collect_qtnetwork_openssl_windows(self, openssl_version):
        """
        Windows-specific collection of OpenSSL DLLs required by QtNetwork module.
        """

        # Package parent path; used to preserve the directory structure when DLLs are collected from the python
        # package (e.g., PyPI wheels).
        package_parent_path = self.package_location.parent

        # The OpenSSL DLLs might be shipped with PyPI wheel (PyQt5), might be available in the environment (msys2,
        # anaconda), or might be expected to be available in the environment (PySide2, PySide6, PyQt6 PyPI wheels).
        #
        # The OpenSSL DLL naming scheme depends on the version:
        #  - OpenSSL 1.0.x: libeay32.dll, ssleay32.dll
        #  - OpenSSL 1.1.x 32-bit: libssl-1_1.dll, libcrypto-1_1.dll
        #  - OpenSSL 1.1.x 64-bit: libssl-1_1-x64.dll, libcrypto-1_1-x64.dll
        #  - OpenSSL 3.0.x 32-bit: libssl-1.dll, libcrypto-3.dll
        #  - OpenSSL 3.0.x 64-bit: libssl-3-x64.dll, libcrypto-3-x64.dll
        #
        # The official Qt builds (which are used by PySide and PyQt PyPI wheels) seem to be build against:
        #  - OpenSSL 1.1.x starting with Qt5 5.14.2:
        #    https://www.qt.io/blog/2019/06/17/qt-5-12-4-released-support-openssl-1-1-1
        #  - OpenSSL 3.x starting with Qt6 6.5.0:
        #    https://www.qt.io/blog/moving-to-openssl-3-in-binary-builds-starting-from-qt-6.5-beta-2
        #
        # However, a package can build Qt against OpenSSL version of their own choice. For example, at the time of
        # writing, both mingw-w64-x86_64-qt5-base 5.15.11+kde+r138-1 and mingw-w64-x86_64-qt6-base 6.6.0-2 packages
        # depend on mingw-w64-x86_64-openssl 3.1.4-1 (so OpenSSL 3).
        #
        # Luckily, we can query the run-time version of OpenSSL by calling `QSslSocket.sslLibraryVersionNumber()`,
        # and narrow down the search for specific version.
        if openssl_version >= 0x10000000 and openssl_version < 0x10100000:
            # OpenSSL 1.0.x - used by old Qt5 builds
            dll_names = (
                'libeay32.dll',
                'ssleay32.dll',
            )
            logger.debug("%s: QtNetwork: looking for OpenSSL 1.0.x DLLs: %r", self, dll_names)
        elif openssl_version >= 0x10100000 and openssl_version < 0x30000000:
            # OpenSSL 1.1.x
            dll_names = (
                'libssl-1_1-x64.dll' if compat.is_64bits else 'libssl-1_1.dll',
                'libcrypto-1_1-x64.dll' if compat.is_64bits else 'libcrypto-1_1.dll',
            )
            logger.debug("%s: QtNetwork: looking for OpenSSL 1.1.x DLLs: %r", self, dll_names)
        elif openssl_version >= 0x30000000 and openssl_version < 0x40000000:
            # OpenSSL 3.0.x
            dll_names = (
                'libssl-3-x64.dll' if compat.is_64bits else 'libssl-3.dll',
                'libcrypto-3-x64.dll' if compat.is_64bits else 'libcrypto-3.dll',
            )
            logger.debug("%s: QtNetwork: looking for OpenSSL 3.0.x DLLs: %r", self, dll_names)
        else:
            dll_names = []  # Nothing to search for
            logger.warning("%s: QtNetwork: unsupported OpenSSL version: %X", self, openssl_version)

        binaries = []
        found_in_package = False
        for dll in dll_names:
            # Attempt to resolve the DLL path
            dll_file_path = bindepend.resolve_library_path(dll, search_paths=[self.qt_lib_dir])
            if dll_file_path is None:
                continue
            dll_file_path = pathlib.Path(dll_file_path).resolve()
            if package_parent_path in dll_file_path.parents:
                # The DLL is located within python package; preserve the layout
                dst_dll_path = dll_file_path.parent.relative_to(package_parent_path)
                found_in_package = True
            else:
                # The DLL is not located within python package; collect into top-level directory
                dst_dll_path = '.'
            binaries.append((str(dll_file_path), str(dst_dll_path)))

        # If we found at least one OpenSSL DLL in the bindings' python package directory, discard all external
        # OpenSSL DLLs.
        if found_in_package:
            binaries = [(dll_src_path, dll_dest_path) for dll_src_path, dll_dest_path in binaries
                        if package_parent_path in pathlib.Path(dll_src_path).parents]

        return binaries

    def _collect_qtnetwork_openssl_macos(self, openssl_version):
        """
        macOS-specific collection of OpenSSL dylibs required by QtNetwork module.
        """

        # The official Qt5 builds on macOS (shipped by PyPI wheels) appear to be built with Apple's SecureTransport API
        # instead of OpenSSL; for example, `QSslSocket.sslLibraryVersionNumber` returns 0, while
        # `sslLibraryVersionString()` returns "Secure Transport, macOS 12.6". So with PySide2 and PyQt5, we do not need
        # to worry about collection of OpenSSL shared libraries.
        #
        # Support for OpenSSL was introduced in Qt 6.1 with `openssl` TLS backend; the official Qt6 builds prior to 6.5
        # seem to be built with OpenSSL 1.1.x, and later versions with 3.0.x. However, PySide6 and PyQt6 PyPI wheels do
        # not ship OpenSSL dynamic libraries at all , so whether `openssl` TLS backend is used or not depends on the
        # presence of externally provided OpenSSL dynamic libraries (for example, provided by Homebrew). It is worth
        # noting that python.org python installers *do* provide OpenSSL shared libraries (1.1.x for python <= 3.10,
        # 3.0.x for python >= 3.12, and both for python 3.11) for its `_ssl` extension - however, these are NOT visible
        # to Qt and its QtNetwork module.
        #
        # When the frozen application is built and we collect python's `_ssl` extension, we also collect the OpenSSL
        # shared libraries shipped by python. So at least in theory, those should be available to QtNetwork module as
        # well (assuming they are of compatible version). However, this is not exactly the case - QtNetwork looks for
        # the libraries in locations given by `DYLD_LIBRARY_PATH` environment variable and in .app/Contents/Frameworks
        # (if the program is an .app bundle):
        #
        # https://github.com/qt/qtbase/blob/6.6.0/src/plugins/tls/openssl/qsslsocket_openssl_symbols.cpp#L590-L599
        #
        # So it works out-of-the box for our .app bundles, because starting with PyInstaller 6.0, `sys._MEIPASS` is in
        # .app/Contents/Frameworks. But it does not with POSIX builds, because bootloader does not modify the
        # `DYLD_LIBRARY_PATH` environment variable to include `sys._MEIPASS` (since we usually do not need that;
        # regular linked library resolution in our macOS builds is done via path rewriting and rpaths). So either we
        # need a run-time hook to add `sys._MEIPASS` to `DYLD_LIBRARY_PATH`, or modify the bootloader to always do that.
        #
        # Collecting the OpenSSL library and making it discoverable by adding `sys._MEIPASS` to `DYLD_LIBRARY_PATH`
        # should also prevent QtNetwork from "accidentally" pulling in Homebrew version at run-time (if Homebrew is
        # installed on the target system and provides compatible OpenSSL version).
        #
        # Therefore, try to resolve OpenSSL library via the version indicated by `QSslSocket.sslLibraryVersionNumber`;
        # however, we first explicitly search only {sys.base_prefix}/lib (which is where python.org builds put their
        # dynamic libs), and only if that fails, perform regular dylib path resolution. This way we ensure that if the
        # OpenSSL dylibs are provided by python itself, we always prefer those over the Homebrew version (since we are
        # very likely going to collect them for python's `_ssl` extension anyway).

        # As per above text, we need to worry only about Qt6, and thus OpenSSL 1.1.x or 3.0.x
        if openssl_version >= 0x10100000 and openssl_version < 0x30000000:
            # OpenSSL 1.1.x
            dylib_names = (
                'libcrypto.1.1.dylib',
                'libssl.1.1.dylib',
            )
            logger.debug("%s: QtNetwork: looking for OpenSSL 1.1.x dylibs: %r", self, dylib_names)
        elif openssl_version >= 0x30000000 and openssl_version < 0x40000000:
            # OpenSSL 3.0.x
            dylib_names = (
                'libcrypto.3.dylib',
                'libssl.3.dylib',
            )
            logger.debug("%s: QtNetwork: looking for OpenSSL 3.0.x dylibs: %r", self, dylib_names)
        else:
            dylib_names = []  # Nothing to search for
            logger.warning("%s: QtNetwork: unsupported OpenSSL version: %X", self, openssl_version)

        # Compared to Windows, we do not have to worry about dylib's path preservation, as these are never part of
        # the package, and are therefore always collected to the top-level application directory.
        binaries = []
        base_prefix_lib_dir = os.path.join(compat.base_prefix, 'lib')
        for dylib in dylib_names:
            # First, attempt to resolve using only {sys.base_prefix}/lib - `bindepend.resolve_library_path` uses
            # standard dyld search semantics and uses the given search paths as fallback (and would therefore
            # favor Homebrew-provided version of the library).
            dylib_path = bindepend._resolve_library_path_in_search_paths(dylib, search_paths=[base_prefix_lib_dir])
            if dylib_path is None:
                dylib_path = bindepend.resolve_library_path(dylib, search_paths=[base_prefix_lib_dir, self.qt_lib_dir])
            if dylib_path is None:
                continue
            binaries.append((str(dylib_path), '.'))

        return binaries

    def _collect_qtnetwork_openssl_linux(self, openssl_version):
        """
        Linux-specific collection of OpenSSL dylibs required by QtNetwork module.
        """

        # Out of the supported OSes, Linux is by far the most straight-forward, because OpenSSL shared libraries are
        # expected to be provided by the system. So we can just use standard library path resolution with library names
        # inferred from the run-time OpenSSL version. At run-time, QtNetwork searches paths from `LD_LIBRARY_PATH`, and
        # on Linux, our bootloader already adds `sys._MEIPASS` to that environment variable.

        if openssl_version >= 0x10000000 and openssl_version < 0x10100000:
            # OpenSSL 1.0.x - used by old Qt5 builds
            shlib_names = (
                'libcrypto.so.10',
                'libssl.so.10',
            )
            logger.debug("%s: QtNetwork: looking for OpenSSL 1.0.x shared libraries: %r", self, shlib_names)
        elif openssl_version >= 0x10100000 and openssl_version < 0x30000000:
            # OpenSSL 1.1.x
            shlib_names = (
                'libcrypto.so.1.1',
                'libssl.so.1.1',
            )
            logger.debug("%s: QtNetwork: looking for OpenSSL 1.1.x shared libraries: %r", self, shlib_names)
        elif openssl_version >= 0x30000000 and openssl_version < 0x40000000:
            # OpenSSL 3.0.x
            shlib_names = (
                'libcrypto.so.3',
                'libssl.so.3',
            )
            logger.debug("%s: QtNetwork: looking for OpenSSL 3.0.x shared libraries: %r", self, shlib_names)
        else:
            shlib_names = []  # Nothing to search for
            logger.warning("%s: QtNetwork: unsupported OpenSSL version: %X", self, openssl_version)

        binaries = []
        for shlib in shlib_names:
            shlib_path = bindepend.resolve_library_path(shlib)
            if shlib_path is None:
                continue
            binaries.append((str(shlib_path), '.'))

        return binaries

    def collect_qtqml_files(self):
        """
        Collect additional binaries and data for QtQml module.
        """

        # No-op if requested Qt-based package is not available.
        if self.version is None:
            return [], []

        # Not all PyQt5/PySide2 installs have QML files. In this case, location['Qml2ImportsPath'] is empty.
        # Furthermore, even if location path is provided, the directory itself may not exist.
        #
        # https://github.com/pyinstaller/pyinstaller/pull/3229#issuecomment-359735031
        # https://github.com/pyinstaller/pyinstaller/issues/3864
        #
        # In Qt 6, Qml2ImportsPath was deprecated in favor of QmlImportsPath. The former is not available in PySide6
        # 6.4.0 anymore (but is in PyQt6 6.4.0). Use the new QmlImportsPath if available.
        if 'QmlImportsPath' in self.location:
            qml_src_dir = self.location['QmlImportsPath']
        else:
            qml_src_dir = self.location['Qml2ImportsPath']
        if not qml_src_dir or not os.path.isdir(qml_src_dir):
            logger.warning('%s: QML directory %r does not exist. QML files not packaged.', self, qml_src_dir)
            return [], []

        qml_src_path = pathlib.Path(qml_src_dir).resolve()
        qml_dest_path = pathlib.PurePath(self.qt_rel_dir) / 'qml'

        binaries = []
        datas = []

        # Helper that computes the destination directory for the given file or directory from a QML plugin directory.
        def _compute_dest_dir(src_filename):
            if src_filename.is_dir():
                rel_path = src_filename.relative_to(qml_src_path)
            else:
                rel_path = src_filename.relative_to(qml_src_path).parent
            return qml_dest_path / rel_path

        # Discover all QML plugin sub-directories by searching for `qmldir` files.
        qmldir_files = qml_src_path.rglob('**/qmldir')
        for qmldir_file in sorted(qmldir_files):
            plugin_dir = qmldir_file.parent
            logger.debug("%s: processing QML plugin directory %s", self, plugin_dir)

            try:
                # Obtain lists of source files (separated into binaries and data files).
                plugin_binaries, plugin_datas = self._process_qml_plugin(qmldir_file)
                # Convert into (src, dest) tuples.
                binaries += [(str(src_file), str(_compute_dest_dir(src_file))) for src_file in plugin_binaries]
                datas += [(str(src_file), str(_compute_dest_dir(src_file))) for src_file in plugin_datas]
            except Exception:
                logger.warning("%s: failed to process QML plugin directory %s", self, plugin_dir, exc_info=True)

        return binaries, datas

    # https://doc.qt.io/qt-6/qtqml-modules-qmldir.html#plugin-declaration
    # [optional] plugin <name> [<path]>
    _qml_plugin_def = re.compile(r"^(?:(?:optional)\s+)?(?:plugin)\s+(?P<name>\w+)(?:\s+(?P<path>\.+))?$")

    def _process_qml_plugin(self, qmldir_file):
        """
        Processes the QML directory corresponding to the given `qmldir` file.

        Returns lists of binaries and data files, but only the source file names. It is up to caller to turn these into
        lists of (src, dest) tuples.
        """
        plugin_dir = qmldir_file.parent

        plugin_binaries = set()

        # Read the `qmldir` file to determine the names of plugin binaries, if any.
        contents = qmldir_file.read_text()
        for line in contents.splitlines():
            m = self._qml_plugin_def.match(line)
            if m is None:
                continue

            plugin_name = m.group("name")
            plugin_path = m.group("path")

            # We currently do not support custom plugin path - neither relative nor absolute (the latter will never
            # be supported, because to make it relocatable, we would need to modify the `qmpldir file`).
            if plugin_path is not None:
                raise Exception(f"Non-empty plugin path ({plugin_path!r} is not supported yet!")

            # Turn the plugin base name into actual shared lib name.
            if compat.is_linux:
                plugin_file = plugin_dir / f"lib{plugin_name}.so"
            elif compat.is_win:
                plugin_file = plugin_dir / f"{plugin_name}.dll"
            elif compat.is_darwin:
                plugin_file = plugin_dir / f"lib{plugin_name}.dylib"
            else:
                continue  # This implicitly disables subsequent validation on unhandled platforms.

            # Warn if plugin file does not exist
            if not plugin_file.is_file():
                logger.warn("%s: QML plugin binary %r does not exist!", str(plugin_file))
                continue

            plugin_binaries.add(plugin_file)

        # Exclude plugins with invalid Qt dependencies.
        invalid_binaries = False
        for plugin_binary in plugin_binaries:
            valid, reason = self._validate_plugin_dependencies(plugin_binary)
            if not valid:
                logger.debug("%s: excluding QML plugin binary %r! Reason: %s", self, str(plugin_binary), reason)
                invalid_binaries = True

        # If there was an invalid binary, discard the plugin.
        if invalid_binaries:
            logger.debug("%s: excluding QML plugin directory %r due to invalid plugin binaries!", self, str(plugin_dir))
            return [], []

        # Generate binaries list.
        binaries = sorted(plugin_binaries)

        # Generate list of data files - all content of this directory, except for the plugin binaries. Sub-directories
        # are included if they do not contain a `qmldir` file (we do not recurse into the directory, but instead pass
        # only its name, leaving the recursion to PyInstaller's built-in expansion of paths returned by hooks).
        datas = []
        for entry in plugin_dir.iterdir():
            if entry.is_file():
                if entry in plugin_binaries:
                    continue
            else:
                if (entry / "qmldir").is_file():
                    continue
            datas.append(entry)

        return binaries, datas

    def collect_qtwebengine_files(self):
        """
        Collect QtWebEngine helper process executable, translations, and resources.
        """

        binaries = []
        datas = []

        # Output directory (varies between PyQt and PySide and among OSes; the difference is abstracted by
        # QtLibraryInfo.qt_rel_dir)
        rel_data_path = self.qt_rel_dir

        is_macos_framework = False
        if compat.is_darwin:
            # Determine if we are dealing with a framework-based Qt build (e.g., PyPI wheels) or a dylib-based one
            # (e.g., Anaconda). The former requires special handling, while the latter is handled in the same way as
            # Windows and Linux builds.
            is_macos_framework = os.path.exists(
                os.path.join(self.location['LibrariesPath'], 'QtWebEngineCore.framework')
            )

        if is_macos_framework:
            # macOS .framework bundle
            src_framework_path = os.path.join(self.location['LibrariesPath'], 'QtWebEngineCore.framework')

            # If Qt libraries are bundled with the package, collect the .framework bundle into corresponding package's
            # subdirectory, because binary dependency analysis will also try to preserve the directory structure.
            # However, if we are collecting from system-wide Qt installation (e.g., Homebrew-installed Qt), the binary
            # depndency analysis will attempt to re-create .framework bundle in top-level directory, so we need to
            # collect the extra files there.
            bundled_qt_libs = pathlib.Path(self.package_location) in pathlib.Path(src_framework_path).parents
            if bundled_qt_libs:
                dst_framework_path = os.path.join(rel_data_path, 'lib/QtWebEngineCore.framework')
            else:
                dst_framework_path = 'QtWebEngineCore.framework'  # In top-level directory

            # Determine the version directory - for now, we assume we are dealing with single-version framework;
            # i.e., the Versions directory contains only a single <version> directory, and Current symlink to it.
            versions = sorted([
                version for version in os.listdir(os.path.join(src_framework_path, 'Versions')) if version != 'Current'
            ])
            if len(versions) == 0:
                raise RuntimeError("Could not determine version of the QtWebEngineCore.framework!")
            elif len(versions) > 1:
                logger.warning(
                    "Found multiple versions in QtWebEngineCore.framework (%r) - using the last one!", versions
                )
            version = versions[-1]

            # Collect the Helpers directory. In well-formed .framework bundles (such as the ones provided by Homebrew),
            # the Helpers directory is located in the versioned directory, and symlinked to the top-level directory.
            src_helpers_path = os.path.join(src_framework_path, 'Versions', version, 'Helpers')
            dst_helpers_path = os.path.join(dst_framework_path, 'Versions', version, 'Helpers')
            if not os.path.exists(src_helpers_path):
                # Alas, the .framework bundles shipped with contemporary PyPI PyQt/PySide wheels are not well-formed
                # (presumably because .whl cannot preserve symlinks?). The Helpers in the top-level directory is in fact
                # the hard copy, and there is either no Helpers in versioned directory, or there is a duplicate.
                # So fall back to collecting from the top-level, but collect into versioned directory in order to
                # be compliant with codesign's expectations.
                src_helpers_path = os.path.join(src_framework_path, 'Helpers')

            helper_datas = hooks.collect_system_data_files(src_helpers_path, dst_helpers_path)

            # Filter out the actual helper executable from datas, and add it to binaries instead. This ensures that it
            # undergoes additional binary processing that rewrites the paths to linked libraries.
            HELPER_EXE = 'QtWebEngineProcess.app/Contents/MacOS/QtWebEngineProcess'
            for src_name, dest_name in helper_datas:
                if src_name.endswith(HELPER_EXE):
                    binaries.append((src_name, dest_name))
                else:
                    datas.append((src_name, dest_name))

            # Collect the Resources directory; same logic is used as with Helpers directory.
            src_resources_path = os.path.join(src_framework_path, 'Versions', version, 'Resources')
            dst_resources_path = os.path.join(dst_framework_path, 'Versions', version, 'Resources')
            if not os.path.exists(src_resources_path):
                src_resources_path = os.path.join(src_framework_path, 'Resources')

            datas += hooks.collect_system_data_files(src_resources_path, dst_resources_path)

            # NOTE: the QtWebEngineProcess helper is actually sought within the `QtWebEngineCore.framework/Helpers`,
            # which ought to be a symlink to `QtWebEngineCore.framework/Versions/Current/Helpers`, where `Current`
            # is also a symlink to the actual version directory, `A`.
            #
            # These symlinks are created automatically when the TOC list of collected resources is post-processed
            # using `PyInstaller.utils.osx.collect_files_from_framework_bundles` helper, so we do not have to
            # worry about them here...
        else:
            # Windows and linux (or Anaconda on macOS)
            locales = 'qtwebengine_locales'
            resources = 'resources'

            # Translations
            datas.append((
                os.path.join(self.location['TranslationsPath'], locales),
                os.path.join(rel_data_path, 'translations', locales),
            ))

            # Resources; ``DataPath`` is the base directory for ``resources``, as per the
            # `docs <https://doc.qt.io/qt-5.10/qtwebengine-deploying.html#deploying-resources>`_.
            datas.append((os.path.join(self.location['DataPath'], resources), os.path.join(rel_data_path, resources)),)

            # Helper process executable (QtWebEngineProcess), located in ``LibraryExecutablesPath``.
            # The target directory is determined as `LibraryExecutablesPath` relative to `PrefixPath`. On Windows,
            # this should handle the differences between PySide2/PySide6 and PyQt5/PyQt6 PyPI wheel layout.
            rel_helper_path = os.path.relpath(self.location['LibraryExecutablesPath'], self.location['PrefixPath'])

            # However, on Linux, we need to account for distribution-packaged Qt, where `LibraryExecutablesPath` might
            # be nested deeper under `PrefixPath` than anticipated (w.r.t. PyPI wheel layout). For example, in Fedora,
            # the helper is located under `/usr/lib64/qt5/libexec/QtWebEngineProcess`, with `PrefixPath` being `/usr`
            # and `LibraryExecutablesPath` being `/usr/lib64/qt5/libexec/`, so the relative path ends up being
            # `lib64/qt5/libexec` instead of just `libexec`. So on linux, we explicitly force the PyPI-compliant
            # layout, by overriding relative helper path to just `libexec`.
            if compat.is_linux and rel_helper_path != "libexec":
                logger.info(
                    "%s: overriding relative destination path of QtWebEngineProcess helper from %r to %r!", self,
                    rel_helper_path, "libexec"
                )
                rel_helper_path = "libexec"

            # Similarly, force the relative helper path for PySide2/PySide6 on Windows to `.`. This is already the case
            # with PyPI PySide Windows wheels. But it is not the case with conda-installed PySide2, where the Qt's
            # `PrefixPath` is for example `C:/Users/<user>/miniconda3/envs/<env-name>/Library`, while the corresponding
            # `LibraryExecutablesPath` is `C:/Users/<user>/miniconda3/envs/<env-name>/Library/bin`.
            if compat.is_win and not self.is_pyqt and rel_helper_path != ".":
                logger.info(
                    "%s: overriding relative destination path of QtWebEngineProcess helper from %r to %r!", self,
                    rel_helper_path, "."
                )
                rel_helper_path = "."

            dest = os.path.normpath(os.path.join(rel_data_path, rel_helper_path))
            binaries.append((os.path.join(self.location['LibraryExecutablesPath'], 'QtWebEngineProcess*'), dest))

            # The helper QtWebEngineProcess executable should have an accompanying qt.conf file that helps it locate the
            # Qt shared libraries. Try collecting it as well
            qt_conf_file = os.path.join(self.location['LibraryExecutablesPath'], 'qt.conf')
            if not os.path.isfile(qt_conf_file):
                # The file seems to have been dropped from Qt 6.3 (and corresponding PySide6 and PyQt6) due to
                # redundancy; however, we still need it in the frozen application - so generate our own.
                from PyInstaller.config import CONF  # workpath
                # Relative path to root prefix of bundled Qt - this corresponds to the "inverse" of `rel_helper_path`
                # variable that we computed earlier.
                if rel_helper_path == '.':
                    rel_prefix = '.'
                else:
                    # Replace each directory component in `rel_helper_path` with `..`.
                    rel_prefix = os.path.join(*['..' for _ in range(len(rel_helper_path.split(os.pathsep)))])
                # We expect the relative path to be either . or .. depending on PySide/PyQt layout; if that is not the
                # case, warn about irregular path.
                if rel_prefix not in ('.', '..'):
                    logger.warning(
                        "%s: unexpected relative Qt prefix path for QtWebEngineProcess qt.conf: %s", self, rel_prefix
                    )
                # The Qt docs on qt.conf (https://doc.qt.io/qt-5/qt-conf.html) recommend using forward slashes on
                # Windows as well, due to backslash having to be escaped. This should not matter as we expect the
                # relative path to be . or .., but you never know...
                if os.sep == '\\':
                    rel_prefix = rel_prefix.replace(os.sep, '/')
                # Create temporary file in workpath
                qt_conf_file = os.path.join(CONF['workpath'], "qt.conf")
                with open(qt_conf_file, 'w', encoding='utf-8') as fp:
                    print("[Paths]", file=fp)
                    print("Prefix = {}".format(rel_prefix), file=fp)
            datas.append((qt_conf_file, dest))

        # Add Linux-specific libraries.
        if compat.is_linux:
            # The automatic library detection fails for `NSS <https://packages.ubuntu.com/search?keywords=libnss3>`_,
            # which is used by QtWebEngine. In some distributions, the ``libnss`` supporting libraries are stored in a
            # subdirectory ``nss``. Since ``libnss`` is not linked against them but loads them dynamically at run-time,
            # we need to search for and add them.
            #
            # Specifically, the files we are looking for are
            #  - libfreebl3.so
            #  - libfreeblpriv3.so
            #  - libnssckbi.so
            #  - libnssdbm3.so
            #  - libsoftokn3.so
            # and they might be in the same directory as ``libnss3.so`` (instead of ``nss`` subdirectory); this is
            # the case even with contemporary Debian releases. See
            # https://packages.debian.org/bullseye/amd64/libnss3/filelist
            # vs.
            # https://packages.debian.org/bookworm/amd64/libnss3/filelist

            # Analyze imports of ``QtWebEngineCore`` extension module, and look for ``libnss3.so`` to determine its
            # parent directory.
            libnss_dir = None
            module_file = hooks.get_module_file_attribute(self.namespace + '.QtWebEngineCore')
            for lib_name, lib_path in bindepend.get_imports(module_file):  # (name, fullpath) tuples
                if lib_path is None:
                    continue  # Skip unresolved libraries
                # Look for ``libnss3.so``.
                if os.path.basename(lib_path).startswith('libnss3.so'):
                    libnss_dir = os.path.dirname(lib_path)
                    break

            # Search for NSS libraries
            logger.debug("%s: QtWebEngineCore is linked against libnss3.so; collecting NSS libraries...", self)
            if libnss_dir is not None:
                # Libraries to search for
                NSS_LIBS = [
                    'libfreebl3.so',
                    'libfreeblpriv3.so',
                    'libnssckbi.so',
                    'libnssdbm3.so',
                    'libsoftokn3.so',
                ]
                # Directories (relative to `libnss_dir`) to search in. Also serve as relative destination paths.
                NSS_LIB_SUBDIRS = [
                    'nss',
                    '.',
                ]

                for subdir in NSS_LIB_SUBDIRS:
                    for lib_name in NSS_LIBS:
                        lib_file = os.path.normpath(os.path.join(libnss_dir, subdir, lib_name))
                        if os.path.isfile(lib_file):
                            logger.debug("%s: collecting NSS library: %r", self, lib_file)
                            binaries.append((lib_file, subdir))

        return binaries, datas


# Provide single instances of this class to avoid each hook constructing its own.
pyqt5_library_info = QtLibraryInfo('PyQt5')
pyqt6_library_info = QtLibraryInfo('PyQt6')
pyside2_library_info = QtLibraryInfo('PySide2')
pyside6_library_info = QtLibraryInfo('PySide6')


def get_qt_library_info(namespace):
    """
    Return QtLibraryInfo instance for the given namespace.
    """
    if namespace == 'PyQt5':
        return pyqt5_library_info
    if namespace == 'PyQt6':
        return pyqt6_library_info
    elif namespace == 'PySide2':
        return pyside2_library_info
    elif namespace == 'PySide6':
        return pyside6_library_info

    raise ValueError(f'Invalid namespace: {namespace}!')


# add_qt_dependencies
# --------------------
# Generic implemnentation that finds the Qt 5/6 dependencies based on the hook name of a PyQt5/PyQt6/PySide2/PySide6
# hook. Returns (hiddenimports, binaries, datas). Typical usage:
# ``hiddenimports, binaries, datas = add_qt5_dependencies(__file__)``.
def add_qt_dependencies(hook_file):
    # Find the module underlying this Qt hook: change ``/path/to/hook-PyQt5.blah.py`` to ``PyQt5.blah``.
    hook_name, hook_ext = os.path.splitext(os.path.basename(hook_file))
    assert hook_ext.startswith('.py')
    assert hook_name.startswith('hook-')
    module_name = hook_name[5:]
    namespace = module_name.split('.')[0]

    # Retrieve Qt library info structure....
    qt_info = get_qt_library_info(namespace)
    # ... and use it to collect module dependencies
    return qt_info.collect_module(module_name)


# add_qt5_dependencies
# --------------------
# Find the Qt5 dependencies based on the hook name of a PySide2/PyQt5 hook. Returns (hiddenimports, binaries, datas).
# Typical usage: ``hiddenimports, binaries, datas = add_qt5_dependencies(__file__)``.
add_qt5_dependencies = add_qt_dependencies  # Use generic implementation

# add_qt6_dependencies
# --------------------
# Find the Qt6 dependencies based on the hook name of a PySide6/PyQt6 hook. Returns (hiddenimports, binaries, datas).
# Typical usage: ``hiddenimports, binaries, datas = add_qt6_dependencies(__file__)``.
add_qt6_dependencies = add_qt_dependencies  # Use generic implementation


# A helper for ensuring that only one Qt bindings package is collected into frozen application. Intended to be called
# from hooks for top-level bindings packages.
def ensure_single_qt_bindings_package(qt_bindings):
    # For the lack of better alternative, use CONF structure. Note that this enforces single bindings for the whole
    # spec file instead of individual Analysis instances!
    from PyInstaller.config import CONF

    seen_qt_bindings = CONF.get("_seen_qt_bindings")
    if seen_qt_bindings is None:
        CONF["_seen_qt_bindings"] = qt_bindings
    elif qt_bindings != seen_qt_bindings:
        # Raise SystemExit to abort build process
        raise SystemExit(
            "Aborting build process due to attempt to collect multiple Qt bindings packages: attempting to run hook "
            f"for {qt_bindings!r}, while hook for {seen_qt_bindings!r} has already been run! PyInstaller does not "
            "support multiple Qt bindings packages in a frozen application - either ensure that the build environment "
            "has only one Qt bindings package installed, or exclude the extraneous bindings packages via the module "
            "exclusion mechanism (--exclude command-line option, or excludes list in the spec file)."
        )


# A helper for generating exclude rules for extraneous Qt bindings. Intended for use in hooks for packages that pull in
# multiple Qt bindings packages due to conditional imports (for example, `matplotlib.backends.qt_compat`, `qtpy`).
def exclude_extraneous_qt_bindings(hook_name, qt_bindings_order=None):
    _QT_BINDINGS = ['PyQt5', 'PySide2', 'PyQt6', 'PySide6']  # Known bindings, and also their preferred order
    _QT_API_ENV = 'QT_API'

    def _create_excludes(selected_bindings):
        return [bindings for bindings in _QT_BINDINGS if bindings != selected_bindings]

    logger.debug("%s: selecting Qt bindings package...", hook_name)

    if not qt_bindings_order:
        qt_bindings_order = _QT_BINDINGS  # Use default preference order

    env_qt_bindings = os.environ.get(_QT_API_ENV)
    if env_qt_bindings is not None and env_qt_bindings not in _QT_BINDINGS:
        logger.warning(
            "%s: ignoring unsupported Qt bindings specified via %s environment variable (supported values: %r)!",
            hook_name, _QT_API_ENV, _QT_BINDINGS
        )
        env_qt_bindings = None

    # First choice: see if a hook for top-level Qt bindings package has already been run; if it has, use that bindings
    # package. Due to check in the `ensure_single_qt_bindings_package` that these hooks use, only one such hook could
    # have been run. This should cover cases when the entry-point script explicitly imports one of Qt bindings before
    # importing a package that supports multiple bindings.
    from PyInstaller.config import CONF
    seen_qt_bindings = CONF.get("_seen_qt_bindings")
    if seen_qt_bindings is not None:
        # If bindings are also specified via environment variable and they differ, display a warning.
        if env_qt_bindings is not None and env_qt_bindings != seen_qt_bindings:
            logger.warning(
                "%s: ignoring %s environment variable (%r) because hook for %r has been run!", hook_name, _QT_API_ENV,
                env_qt_bindings, seen_qt_bindings
            )

        logger.info(
            "%s: selected %r as Qt bindings because hook for %r has been run before.", hook_name, seen_qt_bindings,
            seen_qt_bindings
        )
        return _create_excludes(seen_qt_bindings)

    # Second choice: honor the QT_API environment variable, if it specified a valid Qt bindings package.
    if env_qt_bindings is not None:
        logger.info(
            "%s: selected %r as Qt bindings as specified by the %s environment variable.", hook_name, env_qt_bindings,
            _QT_API_ENV
        )
        return _create_excludes(env_qt_bindings)

    # Third choice: select first available bindings (sorted by the given preference order), and display a warning if
    # multiple bindings are available.
    available_qt_bindings = []
    for bindings_name in qt_bindings_order:
        # Check if bindings are available
        info = get_qt_library_info(bindings_name)
        if info.version is None:
            continue
        available_qt_bindings.append(bindings_name)

    if not available_qt_bindings:
        logger.warning("%s: no Qt bindings are available!", hook_name)
        return []  # No need to generate any excludes...

    selected_qt_bindings = available_qt_bindings[0]
    if len(available_qt_bindings) == 1:
        logger.info("%s: selected %r as the only available Qt bindings.", hook_name, selected_qt_bindings)
    else:
        # Warn on multiple bindings, and tell user to use QT_API environment variable
        logger.warning(
            "%s: selected %r as Qt bindings, but multiple bindings are available: %r. Use the %s environment variable "
            "to select different bindings and suppress this warning.", hook_name, selected_qt_bindings,
            available_qt_bindings, _QT_API_ENV
        )
    return _create_excludes(selected_qt_bindings)
