#!/usr/bin/env python

import os
import sys
import PyInstaller
import PyInstaller.compat as compat
from PyInstaller.compat import set
from PyInstaller.utils import misc

import PyInstaller.log as logging
logger = logging.getLogger('PyInstaller.build.hooks')


def __exec_python_cmd(cmd):
    """
    Executes an externally spawned Python interpreter and returns
    anything that was emitted in the standard output as a single
    string.
    """
    # Prepend PYTHONPATH with pathex
    pp = os.pathsep.join(PyInstaller.__pathex__)
    old_pp = compat.getenv('PYTHONPATH')
    if old_pp:
        pp = os.pathsep.join([pp, old_pp])
    compat.setenv("PYTHONPATH", pp)
    try:
        try:
            txt = compat.exec_python(*cmd)
        except OSError, e:
            raise SystemExit("Execution failed: %s" % e)
    finally:
        if old_pp is not None:
            compat.setenv("PYTHONPATH", old_pp)
        else:
            compat.unsetenv("PYTHONPATH")
    return txt.strip()


def exec_statement(statement):
    """Executes a Python statement in an externally spawned interpreter, and
    returns anything that was emitted in the standard output as a single string.
    """
    cmd = ['-c', statement]
    return __exec_python_cmd(cmd)


def exec_script(scriptfilename, *args):
    """
    Executes a Python script in an externally spawned interpreter, and
    returns anything that was emitted in the standard output as a
    single string.

    To prevent missuse, the script passed to hookutils.exec-script
    must be located in the `hooks` directory.
    """

    if scriptfilename != os.path.basename(scriptfilename):
        raise SystemError("To prevent missuse, the script passed to "
                          "hookutils.exec-script must be located in "
                          "the `hooks` directory.")

    cmd = [os.path.join(os.path.dirname(__file__), scriptfilename)]
    cmd.extend(args)
    return __exec_python_cmd(cmd)


def eval_statement(statement):
    txt = exec_statement(statement).strip()
    if not txt:
        # return an empty string which is "not true" but iterable
        return ''
    return eval(txt)


def eval_script(scriptfilename, *args):
    txt = exec_script(scriptfilename, *args).strip()
    if not txt:
        # return an empty string which is "not true" but iterable
        return ''
    return eval(txt)


def qt4_plugins_dir():
    qt4_plugin_dirs = eval_statement(
        "from PyQt4.QtCore import QCoreApplication;"
        "app=QCoreApplication([]);"
        "print map(unicode,app.libraryPaths())")
    if not qt4_plugin_dirs:
        logger.error("Cannot find PyQt4 plugin directories")
        return ""
    for d in qt4_plugin_dirs:
        if os.path.isdir(d):
            return str(d)  # must be 8-bit chars for one-file builds
    logger.error("Cannot find existing PyQt4 plugin directory")
    return ""


def qt4_phonon_plugins_dir():
    qt4_plugin_dirs = eval_statement(
        "from PyQt4.QtGui import QApplication;"
        "app=QApplication([]); app.setApplicationName('pyinstaller');"
        "from PyQt4.phonon import Phonon;"
        "v=Phonon.VideoPlayer(Phonon.VideoCategory);"
        "print map(unicode,app.libraryPaths())")
    if not qt4_plugin_dirs:
        logger.error("Cannot find PyQt4 phonon plugin directories")
        return ""
    for d in qt4_plugin_dirs:
        if os.path.isdir(d):
            return str(d)  # must be 8-bit chars for one-file builds
    logger.error("Cannot find existing PyQt4 phonon plugin directory")
    return ""


def qt4_plugins_binaries(plugin_type):
    """Return list of dynamic libraries formated for mod.binaries."""
    binaries = []
    pdir = qt4_plugins_dir()
    files = misc.dlls_in_dir(os.path.join(pdir, plugin_type))
    for f in files:
        binaries.append((
            os.path.join('qt4_plugins', plugin_type, os.path.basename(f)),
            f, 'BINARY'))
    return binaries


def qt4_menu_nib_dir():
    """Return path to Qt resource dir qt_menu.nib."""
    menu_dir = ''
    # Detect MacPorts prefix (usually /opt/local).
    # Suppose that PyInstaller is using python from macports.
    macports_prefix = sys.executable.split('/Library')[0]
    # list of directories where to look for qt_menu.nib
    dirs = [
        # Qt4 from MacPorts not compiled as framework.
        os.path.join(macports_prefix, 'lib', 'Resources'),
        # Qt4 from MacPorts compiled as framework.
        os.path.join(macports_prefix, 'libexec', 'qt4-mac', 'lib',
            'QtGui.framework', 'Versions', '4', 'Resources'),
        # Qt4 installed into default location.
        '/Library/Frameworks/QtGui.framework/Resources',
        '/Library/Frameworks/QtGui.framework/Versions/4/Resources',
        '/Library/Frameworks/QtGui.Framework/Versions/Current/Resources',
    ]
    # Check directory existence
    for d in dirs:
        d = os.path.join(d, 'qt_menu.nib')
        if os.path.exists(d):
            menu_dir = d
            break

    if not menu_dir:
        logger.error('Cannont find qt_menu.nib directory')
    return menu_dir


def django_dottedstring_imports(django_root_dir):
    package_name = os.path.basename(django_root_dir)
    compat.setenv("DJANGO_SETTINGS_MODULE", "%s.settings" % package_name)
    return eval_script("django-import-finder.py")


def find_django_root(dir):
    entities = set(os.listdir(dir))
    if "manage.py" in entities and "settings.py" in entities and "urls.py" in entities:
        return [dir]
    else:
        django_root_directories = []
        for entity in entities:
            path_to_analyze = os.path.join(dir, entity)
            if os.path.isdir(path_to_analyze):
                try:
                    dir_entities = os.listdir(path_to_analyze)
                except (IOError, OSError):
                    # silently skip unreadable directories
                    continue
                if "manage.py" in dir_entities and "settings.py" in dir_entities and "urls.py" in dir_entities:
                    django_root_directories.append(path_to_analyze)
        return django_root_directories
