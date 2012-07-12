#!/usr/bin/env python

import glob
import os
import sys
import PyInstaller
import PyInstaller.compat as compat
from PyInstaller.compat import is_darwin, set
from PyInstaller.utils import misc

import PyInstaller.log as logging
logger = logging.getLogger(__name__)


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


def get_pyextension_imports(modname):
    """
    Return list of modules required by binary (C/C++) Python extension.

    Python extension files ends with .so (Unix) or .pyd (Windows).
    It's almost impossible to analyze binary extension and its dependencies.

    Module cannot be imported directly.

    Let's at least try import it in a subprocess and get the diffrence
    in module list from sys.modules.

    This function could be used for 'hiddenimports' in PyInstaller hooks files.
    """

    statement = """
import sys
# Importing distutils filters common modules, especiall in virtualenv.
import distutils
original_modlist = sys.modules.keys()
# When importing this module - sys.modules gets updated.
import %(modname)s
all_modlist = sys.modules.keys()
diff = set(all_modlist) - set(original_modlist)
# Module list contain original modname. We do not need it there.
diff.discard('%(modname)s')
# Print module list to stdout.
print list(diff)
""" % {'modname': modname}
    module_imports = eval_statement(statement)
    

    if not module_imports:
        logger.error('Cannot find imports for module %s' % modname)
        return []  # Means no imports found or looking for imports failed.
    #module_imports = filter(lambda x: not x.startswith('distutils'), module_imports)
    return module_imports


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

    # Qt4 from Homebrew compiled as framework
    import glob
    globpath = '/usr/local/Cellar/qt/4.*/lib/QtGui.framework/Versions/4/Resources'
    qt_homebrew_dirs = glob.glob(globpath)
    dirs += qt_homebrew_dirs

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


def matplotlib_backends():
    """
    Return matplotlib backends availabe in current Python installation.

    All matplotlib backends are hardcoded. We have to try import them
    and return the list of successfully imported backends.
    """
    all_bk = eval_statement('import matplotlib; print matplotlib.rcsetup.all_backends')
    avail_bk = []
    import_statement = """
try:
    __import__('matplotlib.backends.backend_%s')
except ImportError, e:
    print str(e)
"""

    # CocoaAgg backend causes subprocess to exit and thus detection
    # is not reliable. This backend is meaningful only on Mac OS X.
    if not is_darwin and 'CocoaAgg' in all_bk:
        all_bk.remove('CocoaAgg')

    # Try to import every backend in a subprocess.
    for bk in all_bk:
        stdout = exec_statement(import_statement % bk.lower())
        # Backend import is successfull if there is no text in stdout.
        if not stdout:
            avail_bk.append(bk)

    # Convert backend name to module name.
    # e.g. GTKAgg -> backend_gtkagg
    return ['backend_' + x.lower() for x in avail_bk]


def opengl_arrays_modules():
    """
    Return list of array modules for OpenGL module.

    e.g. 'OpenGL.arrays.vbo'
    """
    statement = 'import OpenGL; print OpenGL.__path__[0]'
    opengl_mod_path = PyInstaller.hooks.hookutils.exec_statement(statement)
    arrays_mod_path = os.path.join(opengl_mod_path, 'arrays')
    files = glob.glob(arrays_mod_path + '/*.py')
    modules = []

    for f in files:
        mod = os.path.splitext(os.path.basename(f))[0]
        # Skip __init__ module.
        if mod == '__init__':
            continue
        modules.append('OpenGL.arrays.' + mod)

    return modules
