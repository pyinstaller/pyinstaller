# ----------------------------------------------------------------------------
# Copyright (c) 2005-2021, PyInstaller Development Team.
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
import json
import glob

from PyInstaller.utils import hooks
from PyInstaller.depend import bindepend
from PyInstaller import log as logging
from PyInstaller import compat
from PyInstaller.utils import misc

logger = logging.getLogger(__name__)


# QtLibraryInfo
# --------------
# This class uses introspection to determine the location of Qt files. This is
# essential to deal with the many variants of the PyQt5/6 and PySide2/6
# package, each of which places files in a different location.
# Therefore, this class provides all location-related members of
# `QLibraryInfo <http://doc.qt.io/qt-5/qlibraryinfo.html>`_.
class QtLibraryInfo:
    def __init__(self, namespace):
        if namespace not in ['PyQt5', 'PyQt6', 'PySide2', 'PySide6']:
            raise Exception('Invalid namespace: {0}'.format(namespace))
        self.namespace = namespace
        # Distinction between PyQt5/6 and PySide2/6
        self.is_pyqt = namespace in {'PyQt5', 'PyQt6'}
        # Distinction between Qt5 and Qt6
        self.qt_major = 6 if namespace in {'PyQt6', 'PySide6'} else 5
        # Determine relative path where Qt libraries and data need to
        # be collected in the frozen application. This varies between
        # PyQt5/PyQt6/PySide2/PySide6, their versions, and platforms.
        # NOTE: it is tempting to consider deriving this path as simply the
        # value of QLibraryInfo.PrefixPath, taken relative to the package's
        # root directory. However, we also need to support non-wheel
        # deployments (e.g., with Qt installed in custom path on Windows,
        # or with Qt and PyQt5 installed on linux using native package
        # manager), and in those, the Qt PrefixPath does not reflect
        # the required relative target path for the frozen application.
        if namespace == 'PyQt5':
            # PyQt5 uses PyQt5/Qt on all platforms, or PyQt5/Qt5 from
            # version 5.15.4 on
            if hooks.is_module_satisfies("PyQt5 >= 5.15.4"):
                self.qt_rel_dir = os.path.join('PyQt5', 'Qt5')
            else:
                self.qt_rel_dir = os.path.join('PyQt5', 'Qt')
        elif namespace == 'PyQt6':
            # Similarly to PyQt5, PyQt6 switched from PyQt6/Qt to PyQt6/Qt6
            # in 6.0.3
            if hooks.is_module_satisfies("PyQt6 >= 6.0.3"):
                self.qt_rel_dir = os.path.join('PyQt6', 'Qt6')
            else:
                self.qt_rel_dir = os.path.join('PyQt6', 'Qt')
        elif namespace == 'PySide2':
            # PySide2 uses PySide2/Qt on linux and macOS, and PySide2
            # on Windows
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

    # Initialize most of this class only when values are first requested from
    # it.
    def __getattr__(self, name):
        if 'version' in self.__dict__:
            # Initialization was already done, but requested attribute is not
            # availiable.
            raise AttributeError(name)
        else:
            # Ensure self.version exists, even if PyQt{5,6}/PySide{2,6} cannot
            # be imported. Hooks and util functions use `if .version` to check
            # whether package was imported and other attributes are
            # expected to be available.  This also serves as a marker that
            # initialization was already done.
            self.version = None
            # Get library path information from Qt. See QLibraryInfo_.
            json_str = hooks.exec_statement("""
                import sys

                # exec_statement only captures stdout. If there are
                # errors, capture them to stdout so they can be displayed to the
                # user. Do this early, in case package imports produce stderr
                # output.
                sys.stderr = sys.stdout

                import json
                try:
                    from %s.QtCore import QLibraryInfo, QCoreApplication
                except Exception:
                    print('False')
                    raise SystemExit(0)

                # QLibraryInfo isn't always valid until a QCoreApplication is
                # instantiated.
                app = QCoreApplication(sys.argv)
                # Qt6 deprecated QLibraryInfo.location() in favor of
                # QLibraryInfo.path(), and QLibraryInfo.LibraryLocation
                # enum was replaced by QLibraryInfo.LibraryPath.
                if hasattr(QLibraryInfo, 'path'):
                    # Qt6; enumerate path enum values directly from
                    # the QLibraryInfo.LibraryPath enum.
                    path_names = [x for x in dir(QLibraryInfo.LibraryPath)
                                  if x.endswith('Path')]
                    location = {x: QLibraryInfo.path(
                                getattr(QLibraryInfo.LibraryPath, x))
                                for x in path_names}
                else:
                    # Qt5; in recent versions, location enum values
                    # can be enumeratd from QLibraryInfo.LibraryLocation.
                    # However, in older versions of Qt5 and its python
                    # bindings, that is unavailable. Hence the enumeration
                    # of "*Path"-named members of QLibraryInfo.
                    path_names = [x for x in dir(QLibraryInfo)
                                  if x.endswith('Path')]
                    location = {x: QLibraryInfo.location(
                                getattr(QLibraryInfo, x))
                                for x in path_names}

                # Determine Qt version. Works for Qt 5.8 and later, where
                # QLibraryInfo.version() was introduced.
                try:
                    version = QLibraryInfo.version().segments()
                except AttributeError:
                    version = []
                print(json.dumps({
                    'isDebugBuild': QLibraryInfo.isDebugBuild(),
                    'version': version,
                    'location': location,
                }))
            """ % self.namespace)
            try:
                qli = json.loads(json_str)
            except Exception as e:
                logger.warning('Cannot read QLibraryInfo output: raised %s when '
                               'decoding:\n%s', str(e), json_str)
                qli = {}

            for k, v in qli.items():
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

    :param namespace: Import namespace (PyQt5, PyQt6, PySide2, or PySide6)

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
        raise Exception("""
            Cannot find existing {0} plugin directories
            Paths checked: {1}
            """.format(namespace, ", ".join(paths)))
    return qt_plugin_paths


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
    # dlls_in_dir() grabs all files ending with ``*.dll``, ``*.so`` and
    # ``*.dylib`` in a certain directory. On Windows this would grab debug
    # copies of Qt plugins, which then causes PyInstaller to add a dependency on
    # the Debug CRT *in addition* to the release CRT.
    if compat.is_win:
        files = [f for f in files if not f.endswith("d.dll")]

    logger.debug("Found plugin files %s for plugin %s", files, plugin_type)
    dest_dir = os.path.join(qt_info.qt_rel_dir, 'plugins', plugin_type)
    binaries = [(f, dest_dir) for f in files]
    return binaries


# Qt deployment approach
# ----------------------
# This is the core of PyInstaller's approach to Qt deployment. It's based on:
#
# - Discovering the location of Qt libraries by introspection, using
#   QtLibraryInfo_. This provides compatibility with many variants of Qt5/6
#   (conda, self-compiled, provided by a Linux distro, etc.) and many versions
#   of Qt5/6, all of which vary in the location of Qt files.
# - Placing all frozen PyQt5/6 or PySide2/6 Qt files in a standard subdirectory
#   layout, which matches the layout of the corresponding wheel on PyPI.
#   This is necessary to support Qt installs which are not in a subdirectory
#   of the PyQt5/6 or PySide2/6 wrappers. See ``hooks/rthooks/pyi_rth_qt5.py``
#   for the use of environment variables to establish this layout.
# - Emitting warnings on missing QML and translation files which some
#   installations don't have.
# - Determining additional files needed for deployment by following the Qt
#   deployment process using `_qt_dynamic_dependencies_dict`_ and
#   add_qt_dependencies_.
#
# _qt_dynamic_dependencies_dict
# -----------------------------
# This dictionary provides dynamics dependencies (plugins and translations) that
# can't be discovered using ``getImports``. It was built by combining
# information from:
#
# - Qt `deployment <http://doc.qt.io/qt-5/deployment.html>`_ docs. Specifically:
#
#   -   The `deploying Qt for Linux/X11 <http://doc.qt.io/qt-5/linux-deployment.html#qt-plugins>`_
#       page specifies including the Qt Platform Abstraction (QPA) plugin,
#       ``libqxcb.so``. There's little other guidance provided.
#   -   The `Qt for Windows - Deployment <http://doc.qt.io/qt-5/windows-deployment.html#creating-the-application-package>`_
#       page likewise specifies the ``qwindows.dll`` QPA. This is found by the
#       dependency walker, so it doesn't need to explicitly specified.
#
#       -   For dynamic OpenGL applications, the ``libEGL.dll``,
#           ``libGLESv2.dll``, ``d3dcompiler_XX.dll`` (the XX is a version
#           number), and ``opengl32sw.dll`` libraries are also needed.
#       -   If Qt was configured to use ICU, the ``icudtXX.dll``,
#           ``icuinXX.dll``, and ``icuucXX.dll`` libraries are needed.
#
#       These are included by ``hook-PyQt5.py``.
#
#   -   The `Qt for macOS - Deployment <http://doc.qt.io/qt-5/osx-deployment.html#qt-plugins>`_
#       page specifies the ``libqcocoa.dylib`` QPA, but little else. The
#       `Mac deployment tool <http://doc.qt.io/qt-5/osx-deployment.html#the-mac-deployment-tool>`_
#       provides the following rules:
#
#       -   The platform plugin is always deployed.
#       -   The image format plugins are always deployed.
#       -   The print support plugin is always deployed.
#       -   SQL driver plugins are deployed if the application uses the Qt SQL
#           module.
#       -   Script plugins are deployed if the application uses the Qt Script
#           module.
#       -   The SVG icon plugin is deployed if the application uses the Qt SVG
#           module.
#       -   The accessibility plugin is always deployed.
#
#   -   Per the `Deploying QML Applications <http://doc.qt.io/qt-5/qtquick-deployment.html>`_
#       page, QML-based applications need the ``qml/`` directory available.
#       This is handled by ``hook-PyQt5.QtQuick.py``.
#   -   Per the `Deploying Qt WebEngine Applications <https://doc.qt.io/qt-5.10/qtwebengine-deploying.html>`_
#       page, deployment may include:
#
#       -   Libraries (handled when PyInstaller following dependencies).
#       -   QML imports (if Qt Quick integration is used).
#       -   Qt WebEngine process, which should be located at
#           ``QLibraryInfo::location(QLibraryInfo::LibraryExecutablesPath)``
#           for Windows and Linux, and in ``.app/Helpers/QtWebEngineProcess``
#           for Mac.
#       -   Resources: the files listed in deployWebEngineCore_.
#       -   Translations: on macOS: ``.app/Content/Resources``; on Linux and
#           Windows: ``qtwebengine_locales`` directory in the directory
#           specified by ``QLibraryInfo::location(QLibraryInfo::TranslationsPath)``.
#       -   Audio and video codecs: Probably covered if Qt5Multimedia is
#           referenced?
#
#       This is handled by ``hook-PyQt5.QtWebEngineWidgets.py``.
#
#   -   Since `QAxContainer <http://doc.qt.io/qt-5/activeqt-index.html>`_ is a
#       statically-linked library, it doesn't need any special handling.
#
# - Sources for the `Windows Deployment Tool <http://doc.qt.io/qt-5/windows-deployment.html#the-windows-deployment-tool>`_
#   show more detail:
#
#   -   The `PluginModuleMapping struct <https://code.woboq.org/qt5/qttools/src/windeployqt/main.cpp.html#PluginModuleMapping>`_
#       and the following ``pluginModuleMappings`` global provide a mapping
#       between a plugin directory name and an `enum of Qt plugin names
#       <https://code.woboq.org/qt5/qttools/src/windeployqt/main.cpp.html#QtModule>`_.
#   -   The `QtModuleEntry struct <https://code.woboq.org/qt5/qttools/src/windeployqt/main.cpp.html#QtModuleEntry>`_
#       and ``qtModuleEntries`` global connect this enum to the name of the Qt5
#       library it represents and to the translation files this library
#       requires. (Ignore the ``option`` member -- it's just for command-line
#       parsing.)
#
#   Manually combining these two provides a mapping of Qt library names to the
#   translation and plugin(s) needed by the library. The process is: take the
#   key of the dict below from ``QtModuleEntry.libraryName``, but make it
#   lowercase (since Windows files will be normalized to lowercase). The
#   ``QtModuleEntry.translation`` provides the ``translation_base``. Match the
#   ``QtModuleEntry.module`` with ``PluginModuleMapping.module`` to find the
#   ``PluginModuleMapping.directoryName`` for the required plugin(s).
#
#   -   The `deployWebEngineCore <https://code.woboq.org/qt5/qttools/src/windeployqt/main.cpp.html#_ZL19deployWebEngineCoreRK4QMapI7QStringS0_ERK7OptionsbPS0_>`_
#       function copies the following files from ``resources/``, and also copies
#       the web engine process executable.
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
#   -   Include ``bearer/`` if ``QtNetwork`` is included (and some other
#       condition I didn't look up).
#   -   Always include ``imageformats/``, except for ``qsvg``.
#   -   Include ``imageformats/qsvg`` if ``QtSvg`` is included.
#   -   Always include ``iconengines/``.
#   -   Include ``sqldrivers/`` if ``QtSql`` is included.
#   -   Include ``mediaservice/`` and ``audio/`` if ``QtMultimedia`` is
#       included.
#
#   The always includes will be handled by ``hook-PyQt5.py`` or
#   ``hook-PySide2.py``; optional includes are already covered by the dict
#   below.
#
_qt5_dynamic_dependencies_dict = {
    ## "lib_name":              (.hiddenimports,           translations_base,  zero or more plugins...)
    "qt5bluetooth":             (".QtBluetooth",           None,               ),  # noqa: E241,E202
    "qt5concurrent":            (None,                     "qtbase",           ),
    "qt5core":                  (".QtCore",                "qtbase",           ),
    # This entry generated by hand -- it's not present in the Windows deployment tool sources.
    "qtdbus":                   (".QtDBus",                None,               ),
    "qt5declarative":           (None,                     "qtquick1",         "qml1tooling"),
    "qt5designer":              (".QtDesigner",            None,               ),
    "qt5designercomponents":    (None,                     None,               ),
    "enginio":                  (None,                     None,               ),
    "qt5gamepad":               (None,                     None,               "gamepads"),
    # Note: The ``platformthemes`` plugin is for Linux only, and comes from earlier PyInstaller code in ``hook-PyQt5.QtGui.py``. The ``styles`` plugin comes from the suggestion at https://github.com/pyinstaller/pyinstaller/issues/2156.
    # ``xcbglintegrations`` and ``egldeviceintegrations`` were added manually
    # for linux
    "qt5gui":                   (".QtGui",                 "qtbase",           "accessible", "iconengines", "imageformats", "platforms", "platforminputcontexts", "platformthemes", "styles", "xcbglintegrations", "egldeviceintegrations"),  # noqa
    "qt5help":                  (".QtHelp",                "qt_help",          ),
    # This entry generated by hand -- it's not present in the Windows deployment tool sources.
    "qt5macextras":             (".QtMacExtras",           None,               ),
    "qt5multimedia":            (".QtMultimedia",          "qtmultimedia",     "audio", "mediaservice", "playlistformats"),
    "qt5multimediawidgets":     (".QtMultimediaWidgets",   "qtmultimedia",     ),
    "qt5multimediaquick_p":     (None,                     "qtmultimedia",     ),
    "qt5network":               (".QtNetwork",             "qtbase",           "bearer"),
    "qt5nfc":                   (".QtNfc",                 None,               ),
    "qt5opengl":                (".QtOpenGL",              None,               ),  # noqa
    "qt5positioning":           (".QtPositioning",         None,               "position"),
    "qt5printsupport":          (".QtPrintSupport",        None,               "printsupport"),
    "qt5qml":                   (".QtQml",                 "qtdeclarative",    ),
    "qmltooling":               (None,                     None,               "qmltooling"),
    "qt5quick":                 (".QtQuick",               "qtdeclarative",    "scenegraph", "qmltooling"),  # noqa
    "qt5quickparticles":        (None,                     None,               ),
    "qt5quickwidgets":          (".QtQuickWidgets",        None,               ),
    "qt5script":                (None,                     "qtscript",         ),
    "qt5scripttools":           (None,                     "qtscript",         ),
    "qt5sensors":               (".QtSensors",             None,               "sensors", "sensorgestures"),
    "qt5serialport":            (".QtSerialPort",          "qtserialport",     ),
    "qt5sql":                   (".QtSql",                 "qtbase",           "sqldrivers"),
    "qt5svg":                   (".QtSvg",                 None,               ),
    "qt5test":                  (".QtTest",                "qtbase",           ),
    "qt5webkit":                (None,                     None,               ),
    "qt5webkitwidgets":         (None,                     None,               ),
    "qt5websockets":            (".QtWebSockets",          None,               ),
    "qt5widgets":               (".QtWidgets",             "qtbase",           ),
    "qt5winextras":             (".QtWinExtras",           None,               ),
    "qt5xml":                   (".QtXml",                 "qtbase",           ),
    "qt5xmlpatterns":           (".QXmlPatterns",          "qtxmlpatterns",    ),
    "qt5webenginecore":         (".QtWebEngineCore",       None,               "qtwebengine"),  # noqa
    "qt5webengine":             (".QtWebEngine",           "qtwebengine",      "qtwebengine"),
    "qt5webenginewidgets":      (".QtWebEngineWidgets",    None,               "qtwebengine"),
    "qt53dcore":                (None,                     None,               ),
    "qt53drender":              (None,                     None,               "sceneparsers", "renderplugins", "geometryloaders"),
    "qt53dquick":               (None,                     None,               ),
    "qt53dquickRender":         (None,                     None,               ),
    "qt53dinput":               (None,                     None,               ),
    "qt5location":              (".QtLocation",            None,               "geoservices"),
    "qt5webchannel":            (".QtWebChannel",          None,               ),
    "qt5texttospeech":          (None,                     None,               "texttospeech"),
    "qt5serialbus":             (None,                     None,               "canbus"),
}

# The dynamic dependency dictionary for Qt6 is constructed automatically
# from its Qt5 counterpart, by copying the entries and substituting
# qt5 in the name with qt6. If the entry already exists in the dictionary,
# it is not copied, which allows us to provide Qt6-specific overrides,
# should they prove necessary.
_qt6_dynamic_dependencies_dict = {}

for lib_name, content in _qt5_dynamic_dependencies_dict.items():
    if lib_name.startswith('qt5'):
        lib_name = 'qt6' + lib_name[3:]
    if lib_name not in _qt6_dynamic_dependencies_dict:
        _qt6_dynamic_dependencies_dict[lib_name] = content
del lib_name, content


# add_qt_dependencies
# --------------------
# Generic implemnentation that finds the Qt 5/6 dependencies based on
# the hook name of a PyQt5/PyQt6/PySide2/PySide6 hook. Returns
# (hiddenimports, binaries, datas). Typical usage: ``hiddenimports, binaries,
# datas = add_qt5_dependencies(__file__)``.
def add_qt_dependencies(hook_file):
    # Accumulate all dependencies in a set to avoid duplicates.
    hiddenimports = set()
    translations_base = set()
    plugins = set()

    # Find the module underlying this Qt hook: change
    # ``/path/to/hook-PyQt5.blah.py`` to ``PyQt5.blah``.
    hook_name, hook_ext = os.path.splitext(os.path.basename(hook_file))
    assert hook_ext.startswith('.py')
    assert hook_name.startswith('hook-')
    module_name = hook_name[5:]
    namespace = module_name.split('.')[0]
    # Retrieve Qt library info structure
    qt_info = get_qt_library_info(namespace)

    # Exit if the requested library can't be imported. NOTE: qt_info.version
    # can be empty list on older Qt5 versions (#5381)
    if qt_info.version is None:
        return [], [], []

    # Look up the module returned by this import.
    module = hooks.get_module_file_attribute(module_name)
    logger.debug('add_qt%d_dependencies: Examining %s, based on hook of %s.',
                 qt_info.qt_major, module, hook_file)

    # Walk through all the static dependencies of a dynamically-linked library
    # (``.so``/``.dll``/``.dylib``).
    imports = set(bindepend.getImports(module))
    while imports:
        imp = imports.pop()

        # On Windows, find this library; other platforms already provide the
        # full path.
        if compat.is_win:
            # First, look for Qt binaries in the local Qt install.
            imp = bindepend.getfullnameof(
                imp, qt_info.location['BinariesPath'])

        # Strip off the extension and ``lib`` prefix (Linux/Mac) to give the raw
        # name. Lowercase (since Windows always normalized names to lowercase).
        lib_name = os.path.splitext(os.path.basename(imp))[0].lower()
        # Linux libraries sometimes have a dotted version number --
        # ``libfoo.so.3``. It's now ''libfoo.so``, but the ``.so`` must also be
        # removed.
        if compat.is_linux and os.path.splitext(lib_name)[1] == '.so':
            lib_name = os.path.splitext(lib_name)[0]
        if lib_name.startswith('lib'):
            lib_name = lib_name[3:]
        # Mac: rename from ``qt`` to ``qt5`` or ``qt6`` to match names in
        # Windows/Linux.
        if compat.is_darwin and lib_name.startswith('qt'):
            lib_name = 'qt' + str(qt_info.qt_major) + lib_name[2:]

        # match libs with QT_LIBINFIX set to '_conda', i.e. conda-forge builds
        if lib_name.endswith('_conda'):
            lib_name = lib_name[:-6]

        logger.debug('add_qt%d_dependencies: raw lib %s -> parsed lib %s',
                     qt_info.qt_major, imp, lib_name)

        # Follow only Qt dependencies.
        _qt_dynamic_dependencies_dict = (
            _qt5_dynamic_dependencies_dict if qt_info.qt_major == 5
            else _qt6_dynamic_dependencies_dict)
        if lib_name in _qt_dynamic_dependencies_dict:
            # Follow these to find additional dependencies.
            logger.debug('add_qt%d_dependencies: Import of %s.',
                         qt_info.qt_major, imp)
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
            logger.warning('Unable to find Qt%d translations %s. These '
                           'translations were not packaged.',
                           qt_info.qt_major, src)
    # Change hiddenimports to a list.
    hiddenimports = list(hiddenimports)

    logger.debug('add_qt%d_dependencies: imports from %s:\n'
                 '  hiddenimports = %s\n'
                 '  binaries = %s\n'
                 '  datas = %s',
                 qt_info.qt_major, hook_name, hiddenimports, binaries, datas)
    return hiddenimports, binaries, datas


# add_qt5_dependencies
# --------------------
# Find the Qt5 dependencies based on the hook name of a PySide2/PyQt5 hook.
# Returns (hiddenimports, binaries, datas). Typical usage: ``hiddenimports,
# binaries, datas = add_qt5_dependencies(__file__)``.
add_qt5_dependencies = add_qt_dependencies  # Use generic implementation


# add_qt6_dependencies
# --------------------
# Find the Qt6 dependencies based on the hook name of a PySide6/PyQt6 hook.
# Returns (hiddenimports, binaries, datas). Typical usage: ``hiddenimports,
# binaries, datas = add_qt6_dependencies(__file__)``.
add_qt6_dependencies = add_qt_dependencies  # Use generic implementation


def _find_all_or_none(globs_to_include, num_files, qt_library_info):
    """
    globs_to_include is a list of file name globs
    If the number of found files does not match num_files
    then no files will be included.
    """
    # This function is required because CI is failing to include libEGL. The
    # error in AppVeyor is::
    #
    #   [2312] LOADER: Running pyi_lib_PyQt5-uic.py
    #   Failed to load libEGL (Access is denied.)
    #   More info: https://github.com/pyinstaller/pyinstaller/pull/3568
    #
    # Since old PyQt5 wheels do not include d3dcompiler_4?.dll, libEGL.dll and
    # libGLESv2.dll will not be included for PyQt5 builds during CI.
    to_include = []
    dst_dll_path = '.'
    for dll in globs_to_include:
        # In PyQt5/PyQt6, the DLLs we are looking for are located in
        # location['BinariesPath'], whereas in PySide2/PySide6, they
        # are located in location['PrefixPath'].
        dll_path = os.path.join(qt_library_info.location[
            'BinariesPath' if qt_library_info.is_pyqt else 'PrefixPath'
        ], dll)
        dll_file_paths = glob.glob(dll_path)
        for dll_file_path in dll_file_paths:
            to_include.append((dll_file_path, dst_dll_path))
    if len(to_include) == num_files:
        return to_include
    return []


# Gather required Qt binaries, but only if all binaries in a group exist.
def get_qt_binaries(qt_library_info):
    binaries = []
    angle_files = ['libEGL.dll', 'libGLESv2.dll', 'd3dcompiler_??.dll']
    binaries += _find_all_or_none(angle_files, 3, qt_library_info)

    opengl_software_renderer = ['opengl32sw.dll']
    binaries += _find_all_or_none(opengl_software_renderer, 1, qt_library_info)

    # Include ICU files, if they exist.
    # See the "Deployment approach" section in ``PyInstaller/utils/hooks/qt.py``.
    icu_files = ['icudt??.dll', 'icuin??.dll', 'icuuc??.dll']
    binaries += _find_all_or_none(icu_files, 3, qt_library_info)

    return binaries


# Gather additional shared libraries required for SSL support in QtNetwork,
# if they are available. Applicable only to Windows. See issue #3520, #4048.
def get_qt_network_ssl_binaries(qt_library_info):
    # No-op if requested Qt-based package is not available
    if qt_library_info.version is None:
        return []

    # Applicable only to Windows
    if not compat.is_win:
        return []

    # Check if QtNetwork supports SSL
    ssl_enabled = hooks.eval_statement("""
        from {}.QtNetwork import QSslSocket
        print(QSslSocket.supportsSsl())""".format(qt_library_info.namespace))
    if not ssl_enabled:
        return []

    # PyPI version of PySide2 requires user to manually install SSL
    # libraries into the PrefixPath. Other versions (e.g., the one
    # provided by Conda) put the libraries into the BinariesPath.
    # PyQt5 also uses BinariesPath.
    # Accommodate both options by searching both locations...
    locations = (
        qt_library_info.location['BinariesPath'],
        qt_library_info.location['PrefixPath']
    )
    dll_names = ('libeay32.dll', 'ssleay32.dll', 'libssl-1_1-x64.dll',
                 'libcrypto-1_1-x64.dll')
    binaries = []
    for location in locations:
        for dll in dll_names:
            dll_path = os.path.join(location, dll)
            if os.path.exists(dll_path):
                binaries.append((dll_path, '.'))
    return binaries


# Gather additional binaries and data for QtQml module.
def get_qt_qml_files(qt_library_info):
    # No-op if requested Qt-based package is not available
    if qt_library_info.version is None:
        return [], []

    # Not all PyQt5/PySide2 installs have QML files. In this case,
    # location['Qml2ImportsPath'] is empty. Furthermore, even if location
    # path is provided, the directory itself may not exist.
    #
    # https://github.com/pyinstaller/pyinstaller/pull/3229#issuecomment-359735031
    # https://github.com/pyinstaller/pyinstaller/issues/3864
    qmldir = qt_library_info.location['Qml2ImportsPath']
    if not qmldir or not os.path.exists(qmldir):
        logger.warning('QML directory for %s, %r, does not exist. '
                       'QML files not packaged.', qt_library_info.namespace,
                       qmldir)
        return [], []

    qml_rel_dir = os.path.join(qt_library_info.qt_rel_dir, 'qml')
    datas = [(qmldir, qml_rel_dir)]
    binaries = [
        # Produce ``/path/to/Qt/Qml/path_to_qml_binary/qml_binary,
        # PyQt5/Qt/Qml/path_to_qml_binary``.
        (f, os.path.join(qml_rel_dir,
                         os.path.dirname(os.path.relpath(f, qmldir))))
        for f in misc.dlls_in_subdirs(qmldir)
    ]

    return binaries, datas


# Collect the ``qt.conf`` file.
def get_qt_conf_file(qt_library_info):
    # No-op if requested Qt-based package is not available
    if qt_library_info.version is None:
        return []
    # Find ``qt.conf`` in location['PrefixPath']
    datas = [x for x in hooks.collect_system_data_files(
             qt_library_info.location['PrefixPath'],
             qt_library_info.qt_rel_dir)
             if os.path.basename(x[0]) == 'qt.conf']
    return datas
