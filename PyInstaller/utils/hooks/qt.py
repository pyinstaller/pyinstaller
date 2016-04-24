# ----------------------------------------------------------------------------
# Copyright (c) 2005-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
# ----------------------------------------------------------------------------
import os

from ..hooks import eval_statement, exec_statement, get_homebrew_path
from ... import log as logging
from ...compat import exec_command, is_py3, is_win
from ...utils import misc

logger = logging.getLogger(__name__)


def qt_plugins_dir(namespace):
    """
    Return list of paths searched for plugins.

    :param namespace: Import namespace, i.e., PyQt4, PyQt5, or PySide

    :return: Plugin directory paths
    """
    if namespace not in ['PyQt4', 'PyQt5', 'PySide']:
        raise Exception('Invalid namespace: {0}'.format(namespace))
    paths = eval_statement("""
        from {0}.QtCore import QCoreApplication;
        app = QCoreApplication([]);
        # For Python 2 print would give <PyQt4.QtCore.QStringList
        # object at 0x....>", so we need to convert each element separately
        str = getattr(__builtins__, 'unicode', str);  # for Python 2
        print([str(p) for p in app.libraryPaths()])
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
            """.format(namespace, paths))
    return qt_plugin_paths


def qt_plugins_binaries(plugin_type, namespace):
    """
    Return list of dynamic libraries formatted for mod.binaries.

    :param plugin_type: Plugin to look for
    :param namespace: Import namespace, i.e., PyQt4, PyQt5 or PySide

    :return: Plugin directory path corresponding to the given plugin_type
    """
    if namespace not in ['PyQt4', 'PyQt5', 'PySide']:
        raise Exception('Invalid namespace: {0}'.format(namespace))
    pdir = qt_plugins_dir(namespace=namespace)
    files = []
    for path in pdir:
        files.extend(misc.dlls_in_dir(os.path.join(path, plugin_type)))

    # Windows:
    #
    # dlls_in_dir() grabs all files ending with *.dll, *.so and *.dylib in a certain
    # directory. On Windows this would grab debug copies of Qt plugins, which then
    # causes PyInstaller to add a dependency on the Debug CRT __in addition__ to the
    # release CRT.
    #
    # Since on Windows debug copies of Qt4 plugins end with "d4.dll" and Qt 5 plugins
    # end with "d.dll" we filter them out of the list.
    #
    if is_win and (namespace in ['PyQt4', 'PySide']):
        files = [f for f in files if not f.endswith("d4.dll")]
    elif is_win and namespace is 'PyQt5':
        files = [f for f in files if not f.endswith("d.dll")]

    logger.debug('Found plugin files {0} for plugin \'{1}\''.format(files, plugin_type))
    if namespace in ['PyQt4', 'PySide']:
        plugin_dir = 'qt4_plugins'
    else:
        plugin_dir = 'qt5_plugins'
    dest_dir = os.path.join(plugin_dir, plugin_type)
    binaries = [
        (f, dest_dir)
        for f in files]
    return binaries


def qt_menu_nib_dir(namespace):
    """
    Return path to Qt resource dir qt_menu.nib on OSX only.

    :param namespace: Import namespace, i.e., PyQt4, PyQt5, or PySide

    :return: Directory containing qt_menu.nib for specified namespace
    """
    if namespace not in ['PyQt4', 'PyQt5', 'PySide']:
        raise Exception('Invalid namespace: {0}'.format(namespace))
    menu_dir = None

    path = exec_statement("""
    from {0}.QtCore import QLibraryInfo
    path = QLibraryInfo.location(QLibraryInfo.LibrariesPath)
    str = getattr(__builtins__, 'unicode', str)  # for Python 2
    print(str(path))
    """.format(namespace))
    for location in [os.path.join(path, 'Resources'), os.path.join(path, 'QtGui.framework', 'Resources')]:
        # Check directory existence
        path = os.path.join(location, 'qt_menu.nib')
        if os.path.exists(path):
            menu_dir = path
            logger.debug('Found qt_menu.nib for {0} at {1}'.format(namespace, path))
            break
    if not menu_dir:
        raise Exception("""
            Cannot find qt_menu.nib for {0}
            Path checked: {1}
            """.format(namespace, path))
    return menu_dir


def get_qmake_path(version=''):
    """
    Try to find the path to qmake with version given by the argument as a string.

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
            qmake = os.path.join(directory, 'qmake')
            versionstring = subprocess.check_output([qmake, '-query',
                                                     'QT_VERSION']).strip()
            if is_py3:
                # version string is probably just ASCII
                versionstring = versionstring.decode('utf8')
            if versionstring.find(version) == 0:
                logger.debug('Found qmake version "%s" at "%s".'
                             % (versionstring, qmake))
                return qmake
        except (OSError, subprocess.CalledProcessError):
            pass
    logger.debug('Could not find qmake matching version "%s".' % version)
    return None


def qt5_qml_dir():
    qmake = get_qmake_path('5')
    if qmake is None:
        qmldir = ''
        logger.error('Could not find qmake version 5.x, make sure PATH is '
                     'set correctly or try setting QT5DIR.')
    else:
        qmldir = exec_command(qmake, "-query", "QT_INSTALL_QML").strip()
    if len(qmldir) == 0:
        logger.error('Cannot find QT_INSTALL_QML directory, "qmake -query ' +
                     'QT_INSTALL_QML" returned nothing')
    elif not os.path.exists(qmldir):
        logger.error("Directory QT_INSTALL_QML: %s doesn't exist" % qmldir)

    # 'qmake -query' uses / as the path separator, even on Windows
    qmldir = os.path.normpath(qmldir)
    return qmldir


def qt5_qml_data(directory):
    """
    Return Qml library directory formatted for data.
    """
    qmldir = qt5_qml_dir()
    return os.path.join(qmldir, directory), 'qml'


def qt5_qml_plugins_binaries(directory):
    """
    Return list of dynamic libraries formatted for mod.binaries.
    """
    binaries = []
    qmldir = qt5_qml_dir()

    qt5_qml_plugin_dir = os.path.join(qmldir, directory)
    files = misc.dlls_in_subdirs(qt5_qml_plugin_dir)

    for f in files:
        relpath = os.path.relpath(f, qmldir)
        instdir, file = os.path.split(relpath)
        instdir = os.path.join("qml", instdir)
        logger.debug("qt5_qml_plugins_binaries installing %s in %s"
                     % (f, instdir))
        binaries.append((f, instdir))
    return binaries


def qt5_qml_plugins_datas(directory):
    """
    Return list of data files for mod.binaries. (qmldir, *.qmltypes)
    """
    datas = []
    qmldir = qt5_qml_dir()

    qt5_qml_plugin_dir = os.path.join(qmldir, directory)

    files = []
    for root, _dirs, _files in os.walk(qt5_qml_plugin_dir):
        files.extend(misc.files_in_dir(root, ["qmldir", "*.qmltypes"]))

    for f in files:
        relpath = os.path.relpath(f, qmldir)
        instdir, file = os.path.split(relpath)
        instdir = os.path.join("qml", instdir)
        logger.debug("qt5_qml_plugins_datas installing %s in %s"
                     % (f, instdir))
        datas.append((f, instdir))
    return datas


__all__ = ('qt_plugins_dir', 'qt_plugins_binaries', 'qt_menu_nib_dir', 'get_qmake_path', 'qt5_qml_dir', 'qt5_qml_data',
           'qt5_qml_plugins_binaries', 'qt5_qml_plugins_datas')
