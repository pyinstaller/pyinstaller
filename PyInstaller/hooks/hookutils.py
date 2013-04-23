#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import glob
import os
import sys
import PyInstaller
import PyInstaller.compat as compat
from PyInstaller.compat import is_darwin
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
        pp = os.pathsep.join([old_pp, pp])
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


def exec_script(script_filename, *args):
    """
    Executes a Python script in an externally spawned interpreter, and
    returns anything that was emitted in the standard output as a
    single string.

    To prevent missuse, the script passed to hookutils.exec-script
    must be located in the `hooks/utils` directory.
    """
    script_filename = os.path.join('utils', os.path.basename(script_filename))
    script_filename = os.path.join(os.path.dirname(__file__), script_filename)
    if not os.path.exists(script_filename):
        raise SystemError("To prevent missuse, the script passed to "
                          "hookutils.exec-script must be located in "
                          "the `hooks/utils` directory.")

    # Scripts might be importing some modules. Add PyInstaller code to pathex.
    pyinstaller_root_dir = os.path.dirname(os.path.abspath(PyInstaller.__path__[0]))
    PyInstaller.__pathex__.append(pyinstaller_root_dir)

    cmd = [script_filename]
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
    """
    Get all the necessary Django modules specified in settings.py.

    In the settings.py the modules are specified in several variables
    as strings.
    """
    package_name = os.path.basename(django_root_dir)
    compat.setenv('DJANGO_SETTINGS_MODULE', '%s.settings' % package_name)

    # Extend PYTHONPATH with parent dir of django_root_dir.
    PyInstaller.__pathex__.append(misc.get_path_to_toplevel_modules(django_root_dir))
    # Extend PYTHONPATH with django_root_dir.
    # Many times Django users do not specify absolute imports in the settings module.
    PyInstaller.__pathex__.append(django_root_dir)

    ret = eval_script('django-import-finder.py')

    # Unset environment variables again.
    compat.unsetenv('DJANGO_SETTINGS_MODULE')

    return ret


def django_find_root_dir():
    """
    Return path to directory (top-level Python package) that contains main django
    files. Return None if no directory was detected.

    Main Django project directory contain files like '__init__.py', 'settings.py'
    and 'url.py'.

    In Django 1.4+ the script 'manage.py' is not in the directory with 'settings.py'
    but usually one level up. We need to detect this special case too.
    """
    # Get the directory with manage.py. Manage.py is supplied to PyInstaller as the
    # first main executable script.
    manage_py = sys._PYI_SETTINGS['scripts'][0]
    manage_dir = os.path.dirname(os.path.abspath(manage_py))

    # Get the Django root directory. The directory that contains settings.py and url.py.
    # It could be the directory containig manage.py or any of its subdirectories.
    settings_dir = None
    files = set(os.listdir(manage_dir))
    if 'settings.py' in files and 'urls.py' in files:
        settings_dir = manage_dir
    else:
        for f in files:
            if os.path.isdir(f):
                subfiles = os.listdir(os.path.join(manage_dir, f))
                # Subdirectory contains critical files.
                if 'settings.py' in subfiles and 'urls.py' in subfiles:
                    settings_dir = os.path.join(manage_dir, f)
                    break  # Find the first directory.
    
    return settings_dir


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


def remove_prefix(string, prefix):
    """
    This funtion removes the given prefix from a string, if the string does
    indeed begin with the prefix; otherwise, it returns the string
    unmodified.
    """
    if string.startswith(prefix):
        return string[len(prefix):]
    else:
        return string


def remove_suffix(string, suffix):
    """
    This funtion removes the given suffix from a string, if the string
    does indeed end with the prefix; otherwise, it returns the string
    unmodified.
    """
    # Special case: if suffix is empty, string[:0] returns ''. So, test
    # for a non-empty suffix.
    if suffix and string.endswith(suffix):
        return string[:-len(suffix)]
    else:
        return string


def remove_file_extension(filename):
    """
    This funtion returns filename without its extension.
    """
    return os.path.splitext(filename)[0]


def get_module_file_attribute(package):
    """
    Given a pacage name, return the value of __file__ attribute.

    In PyInstaller process we cannot import directly analyzed modules.
    """
    # Statement to return __file__ attribute of a package.
    __file__statement = """
# Fun Python behavior: __import__('mod.submod') returns mod,
# where as __import__('mod.submod', fromlist = [a non-empty list])
# returns mod.submod. See the docs on `__import__
# <http://docs.python.org/library/functions.html#__import__>`_.
# Keyworded arguments in __import__ function are available
# in Python 2.5+. Compatibility with Python 2.4 is preserved.
_fromlist = ['']
_globals = {}
_locals = {}
package = __import__('%s', _globals, _locals, _fromlist)
print package.__file__
"""
    return exec_statement(__file__statement % package)


def get_package_paths(package):
    """
    Given a package, return the path to packages stored on this machine
    and also returns the path to this particular package. For example,
    if pkg.subpkg lives in /abs/path/to/python/libs, then this function
    returns (/abs/path/to/python/libs,
             /abs/path/to/python/libs/pkg/subpkg).
    """
    # A package must have a path -- check for this, in case the package
    # parameter is actually a module.
    is_pkg_statement = 'import %s as p; print hasattr(p, "__path__")'
    is_package = eval_statement(is_pkg_statement % package)
    assert is_package

    file_attr = get_module_file_attribute(package)

    # package.__file__ = /abs/path/to/package/subpackage/__init__.py.
    # Search for Python files in /abs/path/to/package/subpackage; pkg_dir
    # stores this path.
    pkg_dir = os.path.dirname(file_attr)
    # When found, remove /abs/path/to/ from the filename; mod_base stores
    # this path to be removed.
    pkg_base = remove_suffix(pkg_dir, package.replace('.', os.sep))

    return pkg_base, pkg_dir


# All these extension represent Python modules or extension modules
PY_EXECUTABLE_EXTENSIONS = set(['.py', '.pyc', '.pyd', '.pyo', '.so'])


def collect_submodules(package):
    """
    The following two functions were originally written by Ryan Welsh
    (welchr AT umich.edu).

    This produces a list of strings which specify all the modules in
    package.  Its results can be directly assigned to ``hiddenimports``
    in a hook script; see, for example, hook-sphinx.py. The
    package parameter must be a string which names the package.

    This function does not work on zipped Python eggs.

    This function is used only for hook scripts, but not by the body of
    PyInstaller.
    """
    pkg_base, pkg_dir = get_package_paths(package)
    # Walk through all file in the given package, looking for submodules.
    mods = set()
    for dirpath, dirnames, filenames in os.walk(pkg_dir):
        # Change from OS separators to a dotted Python module path,
        # removing the path up to the package's name. For example,
        # '/abs/path/to/desired_package/sub_package' becomes
        # 'desired_package.sub_package'
        mod_path = remove_prefix(dirpath, pkg_base).replace(os.sep, ".")

        # If this subdirectory is a package, add it and all other .py
        # files in this subdirectory to the list of modules.
        if '__init__.py' in filenames:
            mods.add(mod_path)
            for f in filenames:
                extension = os.path.splitext(f)[1]
                if ((remove_file_extension(f) != '__init__') and
                    extension in PY_EXECUTABLE_EXTENSIONS):
                    mods.add(mod_path + "." + remove_file_extension(f))
        else:
        # If not, nothing here is part of the package; don't visit any of
        # these subdirs.
            del dirnames[:]

    return list(mods)


# These extensions represent Python executables and should therefore be
# ignored.
PY_IGNORE_EXTENSIONS = set(['.py', '.pyc', '.pyd', '.pyo', '.so', 'dylib'])


def collect_data_files(package):
    """
    This routine produces a list of (source, dest) non-Python (i.e. data)
    files which reside in package. Its results can be directly assigned to
    ``datas`` in a hook script; see, for example, hook-sphinx.py. The
    package parameter must be a string which names the package.

    This function does not work on zipped Python eggs.

    This function is used only for hook scripts, but not by the body of
    PyInstaller.
    """
    pkg_base, pkg_dir = get_package_paths(package)
    # Walk through all file in the given package, looking for data files.
    datas = []
    for dirpath, dirnames, files in os.walk(pkg_dir):
        for f in files:
            extension = os.path.splitext(f)[1]
            if not extension in PY_IGNORE_EXTENSIONS:
                # Produce the tuple
                # (/abs/path/to/source/mod/submod/file.dat,
                #  mod/submod/file.dat)
                source = os.path.join(dirpath, f)
                dest = remove_prefix(dirpath,
                                     os.path.dirname(pkg_base) + os.sep)
                datas.append((source, dest))

    return datas
