# ----------------------------------------------------------------------------
# Copyright (c) 2005-2020, PyInstaller Development Team.
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

from ..hooks import eval_statement, exec_statement, get_homebrew_path, \
    get_module_file_attribute
from PyInstaller.depend.bindepend import getImports, getfullnameof
from ... import log as logging
from ...compat import is_win, is_darwin, is_linux
from ...utils import misc

logger = logging.getLogger(__name__)


# Qt5LibraryInfo
# --------------
# This class uses introspection to determine the location of Qt5 files. This is
# essential to deal with the many variants of the PyQt5 package, each of which
# places files in a different location. Therefore, this class provides all
# members of `QLibraryInfo <http://doc.qt.io/qt-5/qlibraryinfo.html>`_.
class Qt5LibraryInfo:
    def __init__(self, namespace):
        if namespace not in ['PyQt5', 'PySide2']:
            raise Exception('Invalid namespace: {0}'.format(namespace))
        self.namespace = namespace
        self.is_PyQt5 = namespace == 'PyQt5'

    # Initialize most of this class only when values are first requested from
    # it.
    def __getattr__(self, name):
        if 'version' in self.__dict__:
            # Initialization was already done, but requested attribute is not
            # availiable.
            raise AttributeError(name)
        else:
            # Ensure self.version exists, even if PyQt5/PySide2 can't be
            # imported. Hooks and util functions use `if .version` to check
            # whether PyQt5/PySide2 was imported and other attributes are
            # expected to be available.  This also serves as a marker that
            # initialization was already done.
            self.version = None
            # Get library path information from Qt. See QLibraryInfo_.
            json_str = exec_statement("""
                import sys

                # exec_statement only captures stdout. If there are
                # errors, capture them to stdout so they can be displayed to the
                # user. Do this early, in case PyQt5 imports produce stderr
                # output.
                sys.stderr = sys.stdout

                import json
                try:
                    from %s.QtCore import QLibraryInfo, QCoreApplication
                except:
                    print('False')
                else:
                    # QLibraryInfo isn't always valid until a QCoreApplication is
                    # instantiated.
                    app = QCoreApplication(sys.argv)
                    paths = [x for x in dir(QLibraryInfo) if x.endswith('Path')]
                    location = {x: QLibraryInfo.location(getattr(QLibraryInfo, x))
                                for x in paths}
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
pyqt5_library_info = Qt5LibraryInfo('PyQt5')
pyside2_library_info = Qt5LibraryInfo('PySide2')


def qt_plugins_dir(namespace):
    """
    Return list of paths searched for plugins.

    :param namespace: Import namespace, i.e., PyQt5 or PySide2

    :return: Plugin directory paths
    """
    if namespace not in ['PyQt5', 'PySide2']:
        raise Exception('Invalid namespace: {0}'.format(namespace))
    if namespace == 'PyQt5':
        paths = [pyqt5_library_info.location['PluginsPath']]
    elif namespace == 'PySide2':
        paths = [pyside2_library_info.location['PluginsPath']]
    else:
        paths = eval_statement("""
            from {0}.QtCore import QCoreApplication;
            app = QCoreApplication([]);
            print(list(app.libraryPaths()))
            """.format(namespace))
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
    :param namespace: Import namespace, i.e., PyQt5 or PySide2

    :return: Plugin directory path corresponding to the given plugin_type
    """
    if namespace not in ['PyQt5', 'PySide2']:
        raise Exception('Invalid namespace: {0}'.format(namespace))
    pdir = qt_plugins_dir(namespace=namespace)
    files = []
    for path in pdir:
        files.extend(misc.dlls_in_dir(os.path.join(path, plugin_type)))

    # Windows:
    #
    # dlls_in_dir() grabs all files ending with ``*.dll``, ``*.so`` and
    # ``*.dylib`` in a certain directory. On Windows this would grab debug
    # copies of Qt plugins, which then causes PyInstaller to add a dependency on
    # the Debug CRT *in addition* to the release CRT.
    if is_win and namespace in ['PyQt5', 'PySide2']:
        files = [f for f in files if not f.endswith("d.dll")]

    logger.debug("Found plugin files %s for plugin %s", files, plugin_type)
    if namespace == 'PyQt5':
        plugin_dir = os.path.join('PyQt5', 'Qt', 'plugins')
    else:
        plugin_dir = os.path.join('PySide2', 'plugins')
    dest_dir = os.path.join(plugin_dir, plugin_type)
    binaries = [(f, dest_dir) for f in files]
    return binaries


def qt_menu_nib_dir(namespace):
    """
    Return path to Qt resource dir qt_menu.nib on OSX only.

    :param namespace: Import namespace, i.e., PyQt5 or PySide2

    :return: Directory containing qt_menu.nib for specified namespace
    """
    if namespace not in ['PyQt5', 'PySide2']:
        raise Exception('Invalid namespace: {0}'.format(namespace))
    menu_dir = None

    path = exec_statement("""
    from {0}.QtCore import QLibraryInfo
    path = QLibraryInfo.location(QLibraryInfo.LibrariesPath)
    print(path)
    """.format(namespace))
    anaconda_path = os.path.join(sys.exec_prefix, "python.app", "Contents",
                                 "Resources")
    paths = [os.path.join(path, 'Resources'),
             os.path.join(path, 'QtGui.framework', 'Resources'), anaconda_path]

    for location in paths:
        # Check directory existence
        path = os.path.join(location, 'qt_menu.nib')
        if os.path.exists(path):
            menu_dir = path
            logger.debug('Found qt_menu.nib for %s at %s', namespace, path)
            break
    if not menu_dir:
        raise Exception("""
            Cannot find qt_menu.nib for {0}
            Path checked: {1}
            """.format(namespace, ", ".join(paths)))
    return menu_dir


def get_qmake_path(version=''):
    """
    Try to find the path to qmake with version given by the argument as a
    string.

    :param version: qmake version
    """
    import subprocess

    # Use QT[45]DIR if specified in the environment
    if 'QT5DIR' in os.environ and version[0] == '5':
        logger.debug('Using $QT5DIR/bin as qmake path')
        return os.path.join(os.environ['QT5DIR'], 'bin', 'qmake')
    if 'QT4DIR' in os.environ and version[0] == '4':
        logger.debug('Using $QT4DIR/bin as qmake path')
        return os.path.join(os.environ['QT4DIR'], 'bin', 'qmake')

    # try the default $PATH
    dirs = ['']

    # try homebrew paths
    for formula in ('qt', 'qt5'):
        homebrewqtpath = get_homebrew_path(formula)
        if homebrewqtpath:
            dirs.append(homebrewqtpath)

    for directory in dirs:
        try:
            qmake = os.path.join(directory, 'bin', 'qmake')
            versionstring = subprocess.check_output([qmake, '-query',
                                                     'QT_VERSION']).strip()
            # version string is probably just ASCII
            versionstring = versionstring.decode('utf8')
            if versionstring.find(version) == 0:
                logger.debug('Found qmake version "%s" at "%s".',
                             versionstring, qmake)
                return qmake
        except (OSError, subprocess.CalledProcessError):
            pass
    logger.debug('Could not find qmake matching version "%s".', version)
    return None


# Qt deployment approach
# ----------------------
# This is the core of PyInstaller's approach to Qt deployment. It's based on:
#
# - Discovering the location of Qt5 libraries by introspection, using
#   Qt5LibraryInfo_. This provides compatibility with many variants of Qt5
#   (conda, self-compiled, provided by a Linux distro, etc.) and many versions
#   of Qt5, all of which vary in the location of Qt5 files.
# - Placing all frozen PyQt5/Qt5 files in a standard subdirectory layout, which
#   matches the layout of the PyQt5 wheel on PyPI. This is necessary to support
#   Qt5 installs which are not in a subdirectory of the PyQt5 wrappers. See
#   ``loader/rthooks/pyi_rth_qt5.py`` for the use of environment variables to
#   establish this layout.
# - Emitting warnings on missing QML and translation files which some
#   installations don't have.
# - Determining additional files needed for deployment by following the Qt
#   deployment process using `_qt_dynamic_dependencies_dict`_ and
#   add_qt5_dependencies_.
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
_qt_dynamic_dependencies_dict = {
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
    "qt5gui":                   (".QtGui",                 "qtbase",           "accessible", "iconengines", "imageformats", "platforms", "platforminputcontexts", "platformthemes", "styles"),
    "qt5help":                  (".QtHelp",                "qt_help",          ),
    # This entry generated by hand -- it's not present in the Windows deployment tool sources.
    "qt5macextras":             (".QtMacExtras",           None,               ),
    "qt5multimedia":            (".QtMultimedia",          "qtmultimedia",     "audio", "mediaservice", "playlistformats"),
    "qt5multimediawidgets":     (".QtMultimediaWidgets",   "qtmultimedia",     ),
    "qt5multimediaquick_p":     (None,                     "qtmultimedia",     ),
    "qt5network":               (".QtNetwork",             "qtbase",           "bearer"),
    "qt5nfc":                   (".QtNfc",                 None,               ),
    ##                                                                              These added manually for Linux.
    "qt5opengl":                (".QtOpenGL",              None,               "xcbglintegrations", "egldeviceintegrations"),
    "qt5positioning":           (".QtPositioning",         None,               "position"),
    "qt5printsupport":          (".QtPrintSupport",        None,               "printsupport"),
    "qt5qml":                   (".QtQml",                 "qtdeclarative",    ),
    "qmltooling":               (None,                     None,               "qmltooling"),
    ##                                                                                                          These added manually for Linux.
    "qt5quick":                 (".QtQuick",               "qtdeclarative",    "scenegraph", "qmltooling", "xcbglintegrations", "egldeviceintegrations"),
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
    ##                                                                                             These added manually for Linux.
    "qt5webenginecore":         (".QtWebEngineCore",       None,               "qtwebengine", "xcbglintegrations", "egldeviceintegrations"),
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


# add_qt5_dependencies
# --------------------
# Find the Qt dependencies based on the hook name of a PyQt5 hook. Returns
# (hiddenimports, binaries, datas). Typical usage: ``hiddenimports, binaries,
# datas = add_qt5_dependencies(__file__)``.
def add_qt5_dependencies(hook_file):
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
    if namespace not in ('PyQt5', 'PySide2'):
        raise Exception('Invalid namespace: {0}'.format(namespace))
    is_PyQt5 = namespace == 'PyQt5'

    # Exit if the requested library can't be imported.
    if ((is_PyQt5 and not pyqt5_library_info.version) or
        (not is_PyQt5 and not pyside2_library_info.version)):
        return [], [], []

    # Look up the module returned by this import.
    module = get_module_file_attribute(module_name)
    logger.debug('add_qt5_dependencies: Examining %s, based on hook of %s.',
                 module, hook_file)

    # Walk through all the static dependencies of a dynamically-linked library
    # (``.so``/``.dll``/``.dylib``).
    imports = set(getImports(module))
    while imports:
        imp = imports.pop()

        # On Windows, find this library; other platforms already provide the
        # full path.
        if is_win:
            imp = getfullnameof(imp,
                # First, look for Qt binaries in the local Qt install.
                pyqt5_library_info.location['BinariesPath'] if is_PyQt5 else
                pyside2_library_info.location['BinariesPath']
            )

        # Strip off the extension and ``lib`` prefix (Linux/Mac) to give the raw
        # name. Lowercase (since Windows always normalized names to lowercase).
        lib_name = os.path.splitext(os.path.basename(imp))[0].lower()
        # Linux libraries sometimes have a dotted version number --
        # ``libfoo.so.3``. It's now ''libfoo.so``, but the ``.so`` must also be
        # removed.
        if is_linux and os.path.splitext(lib_name)[1] == '.so':
            lib_name = os.path.splitext(lib_name)[0]
        if lib_name.startswith('lib'):
            lib_name = lib_name[3:]
        # Mac: rename from ``qt`` to ``qt5`` to match names in Windows/Linux.
        if is_darwin and lib_name.startswith('qt'):
            lib_name = 'qt5' + lib_name[2:]

        # match libs with QT_LIBINFIX set to '_conda', i.e. conda-forge builds
        if lib_name.endswith('_conda'):
            lib_name = lib_name[:-6]

        logger.debug('add_qt5_dependencies: raw lib %s -> parsed lib %s',
                     imp, lib_name)

        # Follow only Qt dependencies.
        if lib_name in _qt_dynamic_dependencies_dict:
            # Follow these to find additional dependencies.
            logger.debug('add_qt5_dependencies: Import of %s.', imp)
            imports.update(getImports(imp))
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
    tp = (
        pyqt5_library_info.location['TranslationsPath'] if is_PyQt5
        else pyside2_library_info.location['TranslationsPath']
    )
    datas = []
    for tb in translations_base:
        src = os.path.join(tp, tb + '_*.qm')
        # Not all PyQt5 installations include translations. See
        # https://github.com/pyinstaller/pyinstaller/pull/3229#issuecomment-359479893
        # and
        # https://github.com/pyinstaller/pyinstaller/issues/2857#issuecomment-368744341.
        if glob.glob(src):
            datas.append((
                src, os.path.join(
                    # The PySide2 Windows wheels place translations in a
                    # different location.
                    namespace, '' if not is_PyQt5 and is_win else 'Qt',
                    'translations'
                )
            ))
        else:
            logger.warning('Unable to find Qt5 translations %s. These '
                           'translations were not packaged.', src)
    # Change hiddenimports to a list.
    hiddenimports = list(hiddenimports)

    logger.debug('add_qt5_dependencies: imports from %s:\n'
                 '  hiddenimports = %s\n'
                 '  binaries = %s\n'
                 '  datas = %s',
                 hook_name, hiddenimports, binaries, datas)
    return hiddenimports, binaries, datas


def find_all_or_none(globs_to_include, num_files, qt_library_info):
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
        dll_path = os.path.join(qt_library_info.location[
            'BinariesPath' if qt_library_info.is_PyQt5 else 'PrefixPath'
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
    binaries += find_all_or_none(angle_files, 3, qt_library_info)

    opengl_software_renderer = ['opengl32sw.dll']
    binaries += find_all_or_none(opengl_software_renderer, 1, qt_library_info)

    # Include ICU files, if they exist.
    # See the "Deployment approach" section in ``PyInstaller/utils/hooks/qt.py``.
    icu_files = ['icudt??.dll', 'icuin??.dll', 'icuuc??.dll']
    binaries += find_all_or_none(icu_files, 3, qt_library_info)

    return binaries


__all__ = ('qt_plugins_dir', 'qt_plugins_binaries', 'qt_menu_nib_dir',
           'get_qmake_path')
