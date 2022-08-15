# ----------------------------------------------------------------------------
# Copyright (c) 2005-2022, PyInstaller Development Team.
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

from PyInstaller import compat
from PyInstaller import isolated
from PyInstaller import log as logging
from PyInstaller.depend import bindepend
from PyInstaller.utils import hooks, misc

logger = logging.getLogger(__name__)


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
            # PyQt5 uses PyQt5/Qt on all platforms, or PyQt5/Qt5 from version 5.15.4 on
            try:
                # The call below might fail with AttributeError on some PyQt5 versions (e.g., 5.9.2 from conda's main
                # channel); missing dist information forces a fallback codepath that tries to check for __version__
                # attribute that does not exist, either. So handle the error gracefully and assume old layout.
                new_layout = hooks.is_module_satisfies("PyQt5 >= 5.15.4")
            except AttributeError:
                new_layout = False
            if new_layout:
                self.qt_rel_dir = os.path.join('PyQt5', 'Qt5')
            else:
                self.qt_rel_dir = os.path.join('PyQt5', 'Qt')
        elif namespace == 'PyQt6':
            # Similarly to PyQt5, PyQt6 switched from PyQt6/Qt to PyQt6/Qt6 in 6.0.3
            try:
                # The call below might fail with AttributeError in case of a partial PyQt6 installation. For example,
                # user installs PyQt6 via pip, which also installs PyQt6-Qt6 and PyQt6-sip. Then they naively uninstall
                # PyQt6 package, which leaves the other two behind. PyQt6 now becomes a namespace package and there is
                # no dist metadata, so a fallback codepath in is_module_satisfies tries to check for __version__
                # attribute that does not exist, either. Handle such errors gracefully and assume new layout (with
                # PyQt6, the new layout is more likely); it does not really matter what layout we assume, as library is
                # not usable anyway, but we do need to be able to return an instance of QtLibraryInfo with "version"
                # attribute set to a falsey value.
                new_layout = hooks.is_module_satisfies("PyQt6 >= 6.0.3")
            except AttributeError:
                new_layout = True
            if new_layout:
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

    # Initialize most of this class only when values are first requested from it.
    def __getattr__(self, name):
        if 'version' in self.__dict__:
            # Initialization was already done, but requested attribute is not available.
            raise AttributeError(name)
        else:
            # Ensure self.version exists, even if PyQt{5,6}/PySide{2,6} cannot be imported. Hooks and util functions use
            # `if .version` to check whether package was imported and other attributes are expected to be available.
            # This also serves as a marker that initialization was already done.
            self.version = None

            # Get library path information from Qt. See QLibraryInfo_.
            @isolated.decorate
            def _read_qt_library_info(package):
                import os
                import importlib

                # Import the Qt-based package
                # equivalent to: from package.QtCore import QLibraryInfo, QCoreApplication
                QtCore = importlib.import_module('.QtCore', package)
                QLibraryInfo = QtCore.QLibraryInfo
                QCoreApplication = QtCore.QCoreApplication

                # QLibraryInfo is not always valid until a QCoreApplication is instantiated.
                app = QCoreApplication([])  # noqa: F841

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
                    'isDebugBuild': QLibraryInfo.isDebugBuild(),
                    'version': version,
                    'location': location,
                    'package_location': package_location,
                }

            try:
                qt_info = _read_qt_library_info(self.namespace)
            except Exception as e:
                logger.warning("Failed to obtain Qt info for %r: %s", self.namespace, e)
                qt_info = {}

            for k, v in qt_info.items():
                setattr(self, k, v)

            return getattr(self, name)


# Provide single instances of this class to avoid each hook constructing its own.
pyqt5_library_info = QtLibraryInfo('PyQt5')
pyqt6_library_info = QtLibraryInfo('PyQt6')
pyside2_library_info = QtLibraryInfo('PySide2')
pyside6_library_info = QtLibraryInfo('PySide6')


def get_qt_library_info(namespace):
    """
    Return Qt5LibraryInfo instance for the given namespace.
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


def qt_plugins_dir(namespace):
    """
    Return list of paths searched for plugins.

    :param namespace: Import namespace (PyQt5, PyQt6, PySide2, or PySide6).

    :return: Plugin directory paths
    """
    qt_info = get_qt_library_info(namespace)
    paths = [qt_info.location['PluginsPath']]
    if not paths:
        raise Exception('Cannot find {0} plugin directories'.format(namespace))
    else:
        valid_paths = []
        for path in paths:
            if os.path.isdir(path):
                valid_paths.append(str(path))  # must be 8-bit chars for one-file builds
        qt_plugin_paths = valid_paths
    if not qt_plugin_paths:
        raise Exception(
            "Cannot find existing {0} plugin directories. Paths checked: {1}".format(namespace, ", ".join(paths))
        )
    return qt_plugin_paths


def _qt_filter_release_plugins(plugin_files):
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
            # If we can find a variant without trailing 'd' in the plugin list, then the DLL we are dealing with is a
            # debug variant and needs to be excluded.
            release_name = os.path.splitext(plugin_basename)[0][:-1] + '.dll'
            if release_name in plugin_basenames:
                continue
        release_plugin_files.append(plugin_filename)
    return release_plugin_files


def qt_plugins_binaries(plugin_type, namespace):
    """
    Return list of dynamic libraries formatted for mod.binaries.

    :param plugin_type: Plugin to look for
    :param namespace: Import namespace (PyQt5, PyQt6, PySide2, or PySide6)

    :return: Plugin directory path corresponding to the given plugin_type
    """
    qt_info = get_qt_library_info(namespace)
    pdir = qt_plugins_dir(namespace)
    files = []
    for path in pdir:
        files.extend(misc.dlls_in_dir(os.path.join(path, plugin_type)))

    # Windows:
    #
    # dlls_in_dir() grabs all files ending with ``*.dll``, ``*.so`` and ``*.dylib`` in a certain directory. On Windows
    # this would grab debug copies of Qt plugins, which then causes PyInstaller to add a dependency on the Debug CRT
    # *in addition* to the release CRT.
    if compat.is_win:
        files = _qt_filter_release_plugins(files)

    logger.debug("Found plugin files %s for plugin %s", files, plugin_type)
    dest_dir = os.path.join(qt_info.qt_rel_dir, 'plugins', plugin_type)
    binaries = [(f, dest_dir) for f in files]
    return binaries


# Qt deployment approach
# ----------------------
# This is the core of PyInstaller's approach to Qt deployment. It's based on:
#
# - Discovering the location of Qt libraries by introspection, using QtLibraryInfo_. This provides compatibility with
#   many variants of Qt5/6 (conda, self-compiled, provided by a Linux distro, etc.) and many versions of Qt5/6, all of
#   which vary in the location of Qt files.

# - Placing all frozen PyQt5/6 or PySide2/6 Qt files in a standard subdirectory layout, which matches the layout of the
#   corresponding wheel on PyPI. This is necessary to support Qt installs which are not in a subdirectory of the PyQt5/6
#   or PySide2/6 wrappers. See ``hooks/rthooks/pyi_rth_qt5.py`` for the use of environment variables to establish this
#   layout.

# - Emitting warnings on missing QML and translation files which some installations don't have.

# - Determining additional files needed for deployment by following the Qt deployment process using
#   _qt_dynamic_dependencies_dict`_ and add_qt_dependencies_.
#
# _qt_dynamic_dependencies_dict
# -----------------------------
# This dictionary provides dynamics dependencies (plugins and translations) that cannot be discovered using
# ``getImports``. It was built by combining information from:
#
# - Qt `deployment <http://doc.qt.io/qt-5/deployment.html>`_ docs. Specifically:
#
#   -   The `deploying Qt for Linux/X11 <http://doc.qt.io/qt-5/linux-deployment.html#qt-plugins>`_ page specifies
#       including the Qt Platform Abstraction (QPA) plugin, ``libqxcb.so``. There's little other guidance provided.
#   -   The `Qt for Windows - Deployment
#       <http://doc.qt.io/qt-5/windows-deployment.html#creating-the-application-package>`_ page likewise specifies
#       the ``qwindows.dll`` QPA. This is found by the dependency walker, so it does not need to explicitly specified.
#
#       -   For dynamic OpenGL applications, the ``libEGL.dll``, ``libGLESv2.dll``, ``d3dcompiler_XX.dll`` (the XX is a
#           version number), and ``opengl32sw.dll`` libraries are also needed.
#       -   If Qt was configured to use ICU, the ``icudtXX.dll``, ``icuinXX.dll``, and ``icuucXX.dll`` libraries are
#           needed.
#
#       These are included by ``hook-PyQt5.py``.
#
#   -   The `Qt for macOS - Deployment <http://doc.qt.io/qt-5/osx-deployment.html#qt-plugins>`_ page specifies the
#       ``libqcocoa.dylib`` QPA, but little else. The `Mac deployment tool
#       <http://doc.qt.io/qt-5/osx-deployment.html#the-mac-deployment-tool>`_ provides the following rules:
#
#       -   The platform plugin is always deployed.
#       -   The image format plugins are always deployed.
#       -   The print support plugin is always deployed.
#       -   SQL driver plugins are deployed if the application uses the Qt SQL module.
#       -   Script plugins are deployed if the application uses the Qt Script module.
#       -   The SVG icon plugin is deployed if the application uses the Qt SVG module.
#       -   The accessibility plugin is always deployed.
#
#   -   Per the `Deploying QML Applications <http://doc.qt.io/qt-5/qtquick-deployment.html>`_ page, QML-based
#       applications need the ``qml/`` directory available.
#
#       This is handled by ``hook-PyQt5.QtQuick.py``.
#
#   -   Per the `Deploying Qt WebEngine Applications <https://doc.qt.io/qt-5.10/qtwebengine-deploying.html>`_
#       page, deployment may include:
#
#       -   Libraries (handled when PyInstaller following dependencies).
#       -   QML imports (if Qt Quick integration is used).
#       -   Qt WebEngine process, which should be located at
#           ``QLibraryInfo::location(QLibraryInfo::LibraryExecutablesPath)``
#           for Windows and Linux, and in ``.app/Helpers/QtWebEngineProcess`` for Mac.
#       -   Resources: the files listed in deployWebEngineCore_.
#       -   Translations: on macOS: ``.app/Content/Resources``; on Linux and Windows: ``qtwebengine_locales``
#           directory in the directory specified by ``QLibraryInfo::location(QLibraryInfo::TranslationsPath)``.
#       -   Audio and video codecs: Probably covered if Qt5Multimedia is referenced?
#
#       This is handled by ``hook-PyQt5.QtWebEngineCore.py``.
#
#   -   Since `QAxContainer <http://doc.qt.io/qt-5/activeqt-index.html>`_ is a statically-linked library, it
#       does not need any special handling.
#
# - Sources for the `Windows Deployment Tool
#   <http://doc.qt.io/qt-5/windows-deployment.html#the-windows-deployment-tool>`_ show more detail:
#
#   -   The `PluginModuleMapping struct
#       <https://code.woboq.org/qt5/qttools/src/windeployqt/main.cpp.html#PluginModuleMapping>`_ and the following
#       ``pluginModuleMappings`` global provide a mapping between a plugin directory name and an `enum of Qt plugin
#       names <https://code.woboq.org/qt5/qttools/src/windeployqt/main.cpp.html#QtModule>`_.
#   -   The `QtModuleEntry struct <https://code.woboq.org/qt5/qttools/src/windeployqt/main.cpp.html#QtModuleEntry>`_
#       and ``qtModuleEntries`` global connect this enum to the name of the Qt5 library it represents and to the
#       translation files this library requires. (Ignore the ``option`` member -- it's just for command-line parsing.)
#
#   Manually combining these two provides a mapping of Qt library names to the translation and plugin(s) needed by the
#   library. The process is: take the key of the dict below from ``QtModuleEntry.libraryName``, but make it lowercase
#   (since Windows files will be normalized to lowercase). The ``QtModuleEntry.translation`` provides the
#   ``translation_base``. Match the ``QtModuleEntry.module`` with ``PluginModuleMapping.module`` to find the
#   ``PluginModuleMapping.directoryName`` for the required plugin(s).
#
#   -   The `deployWebEngineCore
#       <https://code.woboq.org/qt5/qttools/src/windeployqt/main.cpp.html#_ZL19deployWebEngineCoreRK4QMapI7QStringS0_ERK7OptionsbPS0_>`_
#       function copies the following files from ``resources/``, and also copies the web engine process executable.
#
#       -   ``icudtl.dat``
#       -   ``qtwebengine_devtools_resources.pak``
#       -   ``qtwebengine_resources.pak``
#       -   ``qtwebengine_resources_100p.pak``
#       -   ``qtwebengine_resources_200p.pak``
#
# - Sources for the `Mac deployment tool`_ are less helpful. The `deployPlugins
#   <https://code.woboq.org/qt5/qttools/src/macdeployqt/shared/shared.cpp.html#_Z13deployPluginsRK21ApplicationBundleInfoRK7QStringS2_14DeploymentInfob>`_
#   function seems to:
#
#   -   Always include ``platforms/libqcocoa.dylib``.
#   -   Always include ``printsupport/libcocoaprintersupport.dylib``
#   -   Include ``bearer/`` if ``QtNetwork`` is included (and some other condition I didn't look up).
#   -   Always include ``imageformats/``, except for ``qsvg``.
#   -   Include ``imageformats/qsvg`` if ``QtSvg`` is included.
#   -   Always include ``iconengines/``.
#   -   Include ``sqldrivers/`` if ``QtSql`` is included.
#   -   Include ``mediaservice/`` and ``audio/`` if ``QtMultimedia`` is included.
#
#   The always includes will be handled by ``hook-PyQt5.py`` or ``hook-PySide2.py``; optional includes are already
#   covered by the dict below.
#
_qt5_dynamic_dependencies_dict = {
    #- "lib_name":              (.hiddenimports,           translations_base,  zero or more plugins...)
    "qt53dcore":                (None,                     None,               ),  # noqa
    "qt53dinput":               (None,                     None,               ),  # noqa
    "qt53dquick":               (None,                     None,               ),  # noqa
    "qt53dquickrender":         (None,                     None,               ),  # noqa
    "qt53drender":              (None,                     None,               "sceneparsers", "renderplugins", "geometryloaders"),  # noqa
    "qt5bluetooth":             (".QtBluetooth",           None,               ),  # noqa
    "qt5concurrent":            (None,                     "qtbase",           ),  # noqa
    "qt5core":                  (".QtCore",                "qtbase",           ),  # noqa
    "qt5dbus":                  (".QtDBus",                None,               ),  # noqa
    "qt5declarative":           (None,                     "qtquick1",         "qml1tooling"),  # noqa
    "qt5designer":              (".QtDesigner",            None,               ),  # noqa
    "qt5designercomponents":    (None,                     None,               ),  # noqa
    "qt5gamepad":               (None,                     None,               "gamepads"),
    # Qt5Gui:
    # The ``platformthemes`` plugins are available only on Linux.
    # Same goes for ``xcbglintegrations`` and ``egldeviceintegrations`` plugins.
    # The ``wayland-decoration-client``, ``wayland-graphics-integration-client``, and ``wayland-shell-integration``
    # plugins are part of Qt5WaylandClient Qt module, whose shared library (e.g., libQt5WaylandClient.so) is linked
    # by the wayland-related ``platforms`` plugins. Ideally, we would collect these plugins based on the
    # Qt5WaylandClient shared library entry, but as our Qt hook utilities do not scan the plugins using this dictionary,
    # that would not work. So instead we list these plugins under Qt5Gui to achieve pretty much the same end result.
    "qt5gui":                   (".QtGui",                 "qtbase",           "accessible", "iconengines", "imageformats", "platforms", "platforminputcontexts", "platformthemes", "xcbglintegrations", "egldeviceintegrations", "wayland-decoration-client", "wayland-graphics-integration-client", "wayland-shell-integration"),  # noqa
    "qt5help":                  (".QtHelp",                "qt_help",          ),  # noqa
    "qt5location":              (".QtLocation",            None,               "geoservices"),  # noqa
    "qt5macextras":             (".QtMacExtras",           None,               ),  # noqa
    "qt5multimedia":            (".QtMultimedia",          "qtmultimedia",     "audio", "mediaservice", "playlistformats"),  # noqa
    "qt5multimediaquick":       (None,                     "qtmultimedia",     ),  # noqa
    "qt5multimediawidgets":     (".QtMultimediaWidgets",   "qtmultimedia",     ),  # noqa
    "qt5network":               (".QtNetwork",             "qtbase",           "bearer"),  # noqa
    "qt5nfc":                   (".QtNfc",                 None,               ),  # noqa
    "qt5opengl":                (".QtOpenGL",              None,               ),  # noqa
    "qt5positioning":           (".QtPositioning",         None,               "position"),  # noqa
    "qt5printsupport":          (".QtPrintSupport",        None,               "printsupport"),  # noqa
    "qt5qml":                   (".QtQml",                 "qtdeclarative",    ),  # noqa
    "qt5quick":                 (".QtQuick",               "qtdeclarative",    "scenegraph", "qmltooling"),  # noqa
    "qt5quickparticles":        (None,                     None,               ),  # noqa
    "qt5quickwidgets":          (".QtQuickWidgets",        None,               ),  # noqa
    "qt5script":                (None,                     "qtscript",         ),  # noqa
    "qt5scripttools":           (None,                     "qtscript",         ),  # noqa
    "qt5sensors":               (".QtSensors",             None,               "sensors", "sensorgestures"),  # noqa
    "qt5serialbus":             (None,                     None,               "canbus"),  # noqa
    "qt5serialport":            (".QtSerialPort",          "qtserialport",     ),  # noqa
    "qt5sql":                   (".QtSql",                 "qtbase",           "sqldrivers"),  # noqa
    "qt5svg":                   (".QtSvg",                 None,               ),  # noqa
    "qt5test":                  (".QtTest",                "qtbase",           ),  # noqa
    "qt5texttospeech":          (None,                     None,               "texttospeech"),  # noqa
    "qt5webchannel":            (".QtWebChannel",          None,               ),  # noqa
    "qt5webengine":             (".QtWebEngine",           "qtwebengine",      "qtwebengine"),  # noqa
    "qt5webenginecore":         (".QtWebEngineCore",       None,               "qtwebengine"),  # noqa
    "qt5webenginewidgets":      (".QtWebEngineWidgets",    None,               "qtwebengine"),  # noqa
    "qt5webkit":                (None,                     None,               ),  # noqa
    "qt5webkitwidgets":         (None,                     None,               ),  # noqa
    "qt5websockets":            (".QtWebSockets",          None,               ),  # noqa
    "qt5widgets":               (".QtWidgets",             "qtbase",           "styles"),  # noqa
    "qt5winextras":             (".QtWinExtras",           None,               ),  # noqa
    "qt5xml":                   (".QtXml",                 "qtbase",           ),  # noqa
    "qt5xmlpatterns":           (".QXmlPatterns",          "qtxmlpatterns",    ),  # noqa
}  # yapf: disable

# The dynamic dependency dictionary for Qt6 is constructed automatically from its Qt5 counterpart, by copying the
# entries and substituting qt5 in the name with qt6. If the entry already exists in the dictionary, it is not
# copied, which allows us to provide Qt6-specific overrides, should they prove necessary.
_qt6_dynamic_dependencies_dict = {
    # Qt6Network:
    # networkinformationbackends plugins were introduced in Qt 6.1, and renamed to networkinformation in Qt 6.2
    # tls plugins were introduced in Qt 6.2
    "qt6network":               (".QtNetwork",             "qtbase",           "networkinformationbackend", "networkinformation", "tls"),  # noqa
    "qt6openglwidgets":         (".QtOpenGLWidgets",       "qtbase", ),  # noqa
    # QtWebEngineQuick is Qt6-specific replacement for QtWebEngine
    "qt6webenginequick":        (".QtWebEngineQuick",      "qtwebengine",      "qtwebengine"),  # noqa
}  # yapf: disable

for lib_name, content in _qt5_dynamic_dependencies_dict.items():
    if lib_name.startswith('qt5'):
        lib_name = 'qt6' + lib_name[3:]
    if lib_name not in _qt6_dynamic_dependencies_dict:
        _qt6_dynamic_dependencies_dict[lib_name] = content
del lib_name, content


# add_qt_dependencies
# --------------------
# Generic implemnentation that finds the Qt 5/6 dependencies based on the hook name of a PyQt5/PyQt6/PySide2/PySide6
# hook. Returns (hiddenimports, binaries, datas). Typical usage:
# ``hiddenimports, binaries, datas = add_qt5_dependencies(__file__)``.
def add_qt_dependencies(hook_file):
    # Accumulate all dependencies in a set to avoid duplicates.
    hiddenimports = set()
    translations_base = set()
    plugins = set()

    # Find the module underlying this Qt hook: change ``/path/to/hook-PyQt5.blah.py`` to ``PyQt5.blah``.
    hook_name, hook_ext = os.path.splitext(os.path.basename(hook_file))
    assert hook_ext.startswith('.py')
    assert hook_name.startswith('hook-')
    module_name = hook_name[5:]
    namespace = module_name.split('.')[0]
    # Retrieve Qt library info structure.
    qt_info = get_qt_library_info(namespace)

    # Exit if the requested library cannot be imported.
    # NOTE: qt_info.version can be empty list on older Qt5 versions (#5381).
    if qt_info.version is None:
        return [], [], []

    # Look up the module returned by this import.
    module = hooks.get_module_file_attribute(module_name)
    logger.debug('add_qt%d_dependencies: Examining %s, based on hook of %s.', qt_info.qt_major, module, hook_file)

    # Walk through all the static dependencies of a dynamically-linked library (``.so``/``.dll``/``.dylib``).
    imports = set(bindepend.getImports(module))
    while imports:
        imp = imports.pop()

        # On Windows, find this library; other platforms already provide the full path.
        if compat.is_win:
            # First, look for Qt binaries in the local Qt install. For PyQt5 and PyQt6, DLLs should be in BinariesPath,
            # while for PySide2 and PySide6, they should be in PrefixPath.
            dll_location = qt_info.location['BinariesPath' if qt_info.is_pyqt else 'PrefixPath']
            imp = bindepend.getfullnameof(imp, dll_location)

        # Strip off the extension and ``lib`` prefix (Linux/Mac) to give the raw name.
        # Lowercase (since Windows always normalizes names to lowercase).
        lib_name = os.path.splitext(os.path.basename(imp))[0].lower()
        # Linux libraries sometimes have a dotted version number -- ``libfoo.so.3``. It is now ''libfoo.so``,
        # but the ``.so`` must also be removed.
        if compat.is_linux and os.path.splitext(lib_name)[1] == '.so':
            lib_name = os.path.splitext(lib_name)[0]
        if lib_name.startswith('lib'):
            lib_name = lib_name[3:]
        # Mac OS: handle different naming schemes. PyPI wheels ship framework-enabled Qt builds, where shared libraries
        # are part of .framework bundles (e.g., ``PyQt5/Qt5/lib/QtCore.framework/Versions/5/QtCore``). In Anaconda
        # (Py)Qt installations, the shared libraries are installed in environment's library directory, and contain
        # versioned extensions, e.g., ``libQt5Core.5.dylib``.
        if compat.is_darwin:
            if lib_name.startswith('qt') and not lib_name.startswith('qt' + str(qt_info.qt_major)):
                # Qt library from a framework bundle (e.g., ``QtCore``); change prefix from ``qt`` to ``qt5`` or ``qt6``
                # to match names in Windows/Linux.
                lib_name = 'qt' + str(qt_info.qt_major) + lib_name[2:]
            if lib_name.endswith('.' + str(qt_info.qt_major)):
                # Qt library from Anaconda, which originally had versioned extension, e.g., ``libfoo.5.dynlib``.
                # The above processing turned it into ``foo.5``, so we need to remove the last two characters.
                lib_name = lib_name[:-2]

        # Match libs with QT_LIBINFIX set to '_conda', i.e. conda-forge builds.
        if lib_name.endswith('_conda'):
            lib_name = lib_name[:-6]

        logger.debug('add_qt%d_dependencies: raw lib %s -> parsed lib %s', qt_info.qt_major, imp, lib_name)

        # PySide2 and PySide6 on linux seem to link all extension modules against libQt5Core, libQt5Network, and
        # libQt5Qml (or their libQt6* equivalents). While the first two are reasonable, the libQt5Qml dependency pulls
        # in whole QtQml module, along with its data and plugins, which in turn pull in several other Qt libraries,
        # greatly inflating the bundle size (see #6447).
        #
        # Similarly, some extension modules (QtWebChannel, QtWebEngine*) seem to be also linked against libQt5Qml,
        # even when the module can be used without having the whole QtQml module collected.
        #
        # Therefore, we explicitly prevent inclusion of QtQml based on the dynamic library dependency, except for
        # QtQml* and QtQuick* modules, whose use directly implies the use of QtQml.
        if lib_name in ("qt5qml", "qt6qml"):
            short_module_name = module_name.split('.', 1)[-1]  # PySide2.QtModule -> QtModule
            if not short_module_name.startswith(('QtQml', 'QtQuick')):
                logger.debug('add_qt%d_dependencies: Ignoring import of %s.', qt_info.qt_major, imp)
                continue

        # Follow only Qt dependencies.
        _qt_dynamic_dependencies_dict = (
            _qt5_dynamic_dependencies_dict if qt_info.qt_major == 5 else _qt6_dynamic_dependencies_dict
        )
        if lib_name in _qt_dynamic_dependencies_dict:
            # Follow these to find additional dependencies.
            logger.debug('add_qt%d_dependencies: Import of %s.', qt_info.qt_major, imp)
            imports.update(bindepend.getImports(imp))
            # Look up which plugins and translations are needed.
            dd = _qt_dynamic_dependencies_dict[lib_name]
            lib_name_hiddenimports, lib_name_translations_base = dd[:2]
            lib_name_plugins = dd[2:]
            # Add them in.
            if lib_name_hiddenimports:
                hiddenimports.update([namespace + lib_name_hiddenimports])
            plugins.update(lib_name_plugins)
            if lib_name_translations_base:
                translations_base.update([lib_name_translations_base])

    # Change plugins into binaries.
    binaries = []
    for plugin in plugins:
        more_binaries = qt_plugins_binaries(plugin, namespace=namespace)
        binaries.extend(more_binaries)
    # Change translation_base to datas.
    tp = qt_info.location['TranslationsPath']
    tp_dst = os.path.join(qt_info.qt_rel_dir, 'translations')
    datas = []
    for tb in translations_base:
        src = os.path.join(tp, tb + '_*.qm')
        # Not all PyQt5 installations include translations. See
        # https://github.com/pyinstaller/pyinstaller/pull/3229#issuecomment-359479893
        # and
        # https://github.com/pyinstaller/pyinstaller/issues/2857#issuecomment-368744341.
        if glob.glob(src):
            datas.append((src, tp_dst))
        else:
            logger.warning(
                'Unable to find Qt%d translations %s. These translations were not packaged.', qt_info.qt_major, src
            )
    # Change hiddenimports to a list.
    hiddenimports = list(hiddenimports)

    logger.debug(
        'add_qt%d_dependencies: imports from %s:\n'
        '  hiddenimports = %s\n'
        '  binaries = %s\n'
        '  datas = %s', qt_info.qt_major, hook_name, hiddenimports, binaries, datas
    )
    return hiddenimports, binaries, datas


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


def _find_all_or_none(qt_library_info, mandatory_dll_patterns, optional_dll_patterns=None):
    """
    Try to find Qt DLLs from the specified mandatory pattern list. If all mandatory patterns resolve to DLLs, collect
    them all, as well as any DLLs from the optional pattern list. If a mandatory pattern fails to resolve to a DLL,
    return an empty list.

    This allows all-or-none collection of particular groups of Qt DLLs that may or may not be available.
    """
    optional_dll_patterns = optional_dll_patterns or []

    # Resolve path to the the corresponding python package (actually, its parent directory). Used to preserve directory
    # structure when DLLs are collected from the python package (e.g., PyPI wheels).
    package_parent_path = pathlib.Path(qt_library_info.package_location).resolve().parent

    # In PyQt5/PyQt6, the DLLs we are looking for are located in location['BinariesPath'], whereas in PySide2/PySide6,
    # they are located in location['PrefixPath'].
    dll_path = qt_library_info.location['BinariesPath' if qt_library_info.is_pyqt else 'PrefixPath']
    dll_path = pathlib.Path(dll_path).resolve()

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
def get_qt_binaries(qt_library_info):
    binaries = []

    # Applicable only to Windows.
    if not compat.is_win:
        return []

    # OpenGL: EGL/GLES via ANGLE, software OpenGL renderer.
    binaries += _find_all_or_none(qt_library_info, ['libEGL.dll', 'libGLESv2.dll'], ['d3dcompiler_??.dll'])
    binaries += _find_all_or_none(qt_library_info, ['opengl32sw.dll'])

    # Include ICU files, if they exist.
    # See the "Deployment approach" section in ``PyInstaller/utils/hooks/qt.py``.
    binaries += _find_all_or_none(qt_library_info, ['icudt??.dll', 'icuin??.dll', 'icuuc??.dll'])

    return binaries


# Collect additional shared libraries required for SSL support in QtNetwork, if they are available.
# Applicable only to Windows. See issue #3520, #4048.
def get_qt_network_ssl_binaries(qt_library_info):
    # No-op if requested Qt-based package is not available.
    if qt_library_info.version is None:
        return []

    # Applicable only to Windows.
    if not compat.is_win:
        return []

    # Check if QtNetwork supports SSL.
    ssl_enabled = hooks.eval_statement(
        """
        from {}.QtNetwork import QSslSocket
        print(QSslSocket.supportsSsl())
        """.format(qt_library_info.namespace)
    )
    if not ssl_enabled:
        return []

    # Resolve path to the the corresponding python package (actually, its parent directory). Used to preserve directory
    # structure when DLLs are collected from the python package (e.g., PyPI wheels).
    package_parent_path = pathlib.Path(qt_library_info.package_location).resolve().parent

    # PyPI version of PySide2 requires user to manually install SSL libraries into the PrefixPath. Other versions
    # (e.g., the one provided by Conda) put the libraries into the BinariesPath. PyQt5 also uses BinariesPath.
    # Accommodate both options by searching both locations...
    locations = (qt_library_info.location['BinariesPath'], qt_library_info.location['PrefixPath'])
    dll_names = ('libeay32.dll', 'ssleay32.dll', 'libssl-1_1-x64.dll', 'libcrypto-1_1-x64.dll')
    binaries = []
    for location in locations:
        location = pathlib.Path(location).resolve()
        for dll in dll_names:
            dll_file_path = location / dll
            if not dll_file_path.exists():
                continue
            if package_parent_path in dll_file_path.parents:
                # The DLL is located within python package; preserve the layout
                dst_dll_path = dll_file_path.parent.relative_to(package_parent_path)
            else:
                # The DLL is not located within python package; collect into top-level directory
                dst_dll_path = '.'
            binaries.append((str(dll_file_path), str(dst_dll_path)))
    return binaries


# Collect additional binaries and data for QtQml module.
def get_qt_qml_files(qt_library_info):
    # No-op if requested Qt-based package is not available.
    if qt_library_info.version is None:
        return [], []

    # Not all PyQt5/PySide2 installs have QML files. In this case, location['Qml2ImportsPath'] is empty.
    # Furthermore, even if location path is provided, the directory itself may not exist.
    #
    # https://github.com/pyinstaller/pyinstaller/pull/3229#issuecomment-359735031
    # https://github.com/pyinstaller/pyinstaller/issues/3864
    qmldir = qt_library_info.location['Qml2ImportsPath']
    if not qmldir or not os.path.exists(qmldir):
        logger.warning(
            'QML directory for %s, %r, does not exist. QML files not packaged.', qt_library_info.namespace, qmldir
        )
        return [], []

    qml_rel_dir = os.path.join(qt_library_info.qt_rel_dir, 'qml')
    datas = [(qmldir, qml_rel_dir)]
    binaries = [
        # Produce ``/path/to/Qt/Qml/path_to_qml_binary/qml_binary, PyQt5/Qt/Qml/path_to_qml_binary``.
        (f, os.path.join(qml_rel_dir, os.path.dirname(os.path.relpath(f, qmldir))))
        for f in misc.dlls_in_subdirs(qmldir)
    ]

    return binaries, datas


# Collect QtWebEngine helper process executable, translations, and resources.
def get_qt_webengine_binaries_and_data_files(qt_library_info):
    binaries = []
    datas = []

    # Output directory (varies between PyQt and PySide and among OSes; the difference is abstracted by
    # qt_library_info.qt_rel_dir)
    rel_data_path = qt_library_info.qt_rel_dir

    is_macos_framework = False
    if compat.is_darwin:
        # Determine if we are dealing with a framework-based Qt build (e.g., PyPI wheels) or a dylib-based one
        # (e.g., Anaconda). The former requires special handling, while the latter is handled in the same way as
        # Windows and Linux builds.
        is_macos_framework = os.path.exists(
            os.path.join(qt_library_info.location['LibrariesPath'], 'QtWebEngineCore.framework')
        )

    if is_macos_framework:
        # On macOS, Qt shared libraries are provided in form of .framework bundles. However, PyInstaller collects shared
        # library from the bundle into top-level application directory, breaking the bundle structure.
        #
        # QtWebEngine and its underlying Chromium engine, however, have very strict data file layout requirements due to
        # sandboxing, and does not work if the helper process executable does not load the shared library from
        # QtWebEngineCore.framework (which also needs to contain all resources).
        #
        # Therefore, we collect the QtWebEngineCore.framework manually, in order to obtain a working QtWebEngineProcess
        # helper executable. But because that bypasses our dependency scanner, we need to collect the dependent
        # .framework bundles as well. And we need to override QTWEBENGINEPROCESS_PATH in rthook, because the
        # QtWebEngine python extensions actually load up the copy of shared library that is located in
        # sys._MEIPASS (as opposed to the manually-copied one in .framework bundle). Furthermore, because the extension
        # modules use Qt shared libraries in sys._MEIPASS, we also copy all contents of
        # QtWebEngineCore.framework/Resources into sys._MEIPASS to make resource loading in the main process work.
        #
        # Besides being ugly, this approach has three main ramifications:
        # 1. we bundle two copies of each Qt shared library involved: the copy used by main process, picked up by
        #    dependency scanner; and a copy in manually-collected .framework bundle that is used by the helper process.
        # 2. the trick with copying contents of Resource directory of QtWebEngineCore.framework does not work in onefile
        #    mode, and consequently QtWebEngine does not work in onefile mode.
        # 3. copying contents of QtWebEngineCore.framework/Resource means that its Info.plist ends up in sys._MEIPASS,
        #    causing the main process in onedir mode to be mis-identified as "QtWebEngineProcess".
        #
        # In the near future, this quagmire will hopefully be properly sorted out, but in the mean time, we have to live
        # with what we have been given.
        data_path = qt_library_info.location['DataPath']
        libraries = [
            'QtCore', 'QtWebEngineCore', 'QtQuick', 'QtQml', 'QtQmlModels', 'QtNetwork', 'QtGui', 'QtWebChannel',
            'QtPositioning'
        ]
        if qt_library_info.qt_major == 6:
            libraries.extend(['QtOpenGL', 'QtDBus'])
        for i in libraries:
            framework_dir = i + '.framework'
            datas += hooks.collect_system_data_files(
                os.path.join(data_path, 'lib', framework_dir), os.path.join(rel_data_path, 'lib', framework_dir), True
            )
        datas += [(os.path.join(data_path, 'lib', 'QtWebEngineCore.framework', 'Resources'), os.curdir)]
    else:
        # Windows and linux (or Anaconda on macOS)
        locales = 'qtwebengine_locales'
        resources = 'resources'

        # Translations
        datas.append((
            os.path.join(qt_library_info.location['TranslationsPath'], locales),
            os.path.join(rel_data_path, 'translations', locales),
        ))

        # Resources; ``DataPath`` is the base directory for ``resources``, as per the
        # `docs <https://doc.qt.io/qt-5.10/qtwebengine-deploying.html#deploying-resources>`_.
        datas.append(
            (os.path.join(qt_library_info.location['DataPath'], resources), os.path.join(rel_data_path, resources)),
        )

        # Helper process executable (QtWebEngineProcess), located in ``LibraryExecutablesPath``.
        dest = os.path.join(
            rel_data_path,
            os.path.relpath(qt_library_info.location['LibraryExecutablesPath'], qt_library_info.location['PrefixPath'])
        )
        binaries.append((os.path.join(qt_library_info.location['LibraryExecutablesPath'], 'QtWebEngineProcess*'), dest))

        # The helper QtWebEngineProcess executable should have an accompanying qt.conf file that helps it locate the
        # Qt shared libraries. Try collecting it as well
        qt_conf_file = os.path.join(qt_library_info.location['LibraryExecutablesPath'], 'qt.conf')
        if not os.path.isfile(qt_conf_file):
            # The file seems to have been dropped from Qt 6.3 (and corresponding PySide6 and PyQt6) due to redundancy;
            # however, we still need it in the frozen application - so generate our own.
            from PyInstaller.config import CONF  # workpath
            # Relative path to root prefix of bundled Qt
            rel_prefix = os.path.relpath(
                qt_library_info.location['PrefixPath'], qt_library_info.location['LibraryExecutablesPath']
            )
            # We expect the relative path to be either . or .. depending on PySide/PyQt layout; if that is not the case,
            # warn about irregular path
            if rel_prefix not in ('.', '..'):
                logger.warning("Unexpected relative Qt prefix path for QtWebEngineProcess qt.conf: %s", rel_prefix)
            # The Qt docs on qt.conf (https://doc.qt.io/qt-5/qt-conf.html) recommend using forward slashes on Windows
            # as well, due to backslash having to be escaped. This should not matter as we expect the relative path
            # to be . or .., but you never know...
            if os.sep == '\\':
                rel_prefix = rel_prefix.replace(os.sep, '/')
            # Create temporary file in workpath
            qt_conf_file = os.path.join(CONF['workpath'], "qt.conf")
            with open(qt_conf_file, 'w') as fp:
                print("[Paths]", file=fp)
                print("Prefix = {}".format(rel_prefix), file=fp)
        datas.append((qt_conf_file, dest))

    # Add Linux-specific libraries.
    if compat.is_linux:
        # The automatic library detection fails for `NSS <https://packages.ubuntu.com/search?keywords=libnss3>`_, which
        # is used by QtWebEngine. In some distributions, the ``libnss`` supporting libraries are stored in a
        # subdirectory ``nss``. Since ``libnss`` is not statically linked to these, but dynamically loads them, we need
        # to search for and add them.

        # First, get all libraries linked to ``QtWebEngineCore`` extension module.
        module_file = hooks.get_module_file_attribute(qt_library_info.namespace + '.QtWebEngineCore')
        module_imports = bindepend.getImports(module_file)
        for imp in module_imports:
            # Look for ``libnss3.so``.
            if os.path.basename(imp).startswith('libnss3.so'):
                # Find the location of NSS: given a ``/path/to/libnss.so``, add ``/path/to/nss/*.so`` to get the
                # missing NSS libraries.
                nss_glob = os.path.join(os.path.dirname(imp), 'nss', '*.so')
                if glob.glob(nss_glob):
                    binaries.append((nss_glob, 'nss'))

    return binaries, datas
