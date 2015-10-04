#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import copy
import glob
import pkgutil
import os
import pkg_resources
import re
import sys

from ... import compat
from ...compat import is_py2, is_win, is_py3, is_darwin
from ...config import CONF
from ...utils import misc
from ... import HOMEPATH
from ... import log as logging

logger = logging.getLogger(__name__)


# All these extension represent Python modules or extension modules
PY_EXECUTABLE_SUFFIXES = set(['.py', '.pyc', '.pyd', '.pyo', '.so'])

# These extensions represent Python executables and should therefore be
# ignored when collecting data files.
# NOTE: .dylib files are not Python executable and should not be in this list.
PY_IGNORE_EXTENSIONS = set(['.py', '.pyc', '.pyd', '.pyo', '.so'])

# Some hooks need to save some values. This is the dict that can be used for
# that.
#
# When running tests this variable should be reset before every test.
#
# For example the 'wx' module needs variable 'wxpubsub'. This tells PyInstaller
# which protocol of the wx module should be bundled.
hook_variables = {}


def __exec_python_cmd(cmd, env=None):
    """
    Executes an externally spawned Python interpreter and returns
    anything that was emitted in the standard output as a single
    string.
    """
    from ...config import CONF
    if env is None:
        env = {}
    # Update environment. Defaults to 'os.environ'
    pp_env = copy.deepcopy(os.environ)
    pp_env.update(env)
    # Prepend PYTHONPATH with pathex
    # Some functions use some PyInstaller code in subprocess so add
    # PyInstaller HOMEPATH to sys.path too.
    pp = os.pathsep.join(CONF['pathex'] + [HOMEPATH])

    # On Python 2, `os.environ` may only contain bytes.
    # Encode unicode filenames using FS encoding.
    # TODO: `os.environ` wrapper that encodes automatically?
    if is_py2:
        if isinstance(pp, unicode):
            pp = pp.encode(sys.getfilesystemencoding())

    # PYTHONPATH might be already defined in the 'env' argument. Prepend it.
    if 'PYTHONPATH' in env:
        pp = os.pathsep.join([env.get('PYTHONPATH'), pp])
    pp_env['PYTHONPATH'] = pp

    try:
        txt = compat.exec_python(*cmd, env=pp_env)
    except OSError as e:
        raise SystemExit("Execution failed: %s" % e)
    return txt.strip()


def exec_statement(statement):
    """Executes a Python statement in an externally spawned interpreter, and
    returns anything that was emitted in the standard output as a single string.
    """
    cmd = ['-c', statement]
    return __exec_python_cmd(cmd)


def exec_script(script_filename, env={}, *args):
    """
    Executes a Python script in an externally spawned interpreter, and
    returns anything that was emitted in the standard output as a
    single string.

    To prevent missuse, the script passed to hookutils.exec_script
    must be located in the `PyInstaller/utils/hooks/subproc` directory.
    """
    script_filename = os.path.basename(script_filename)
    script_filename = os.path.join(os.path.dirname(__file__), 'subproc', script_filename)
    if not os.path.exists(script_filename):
        raise SystemError("To prevent missuse, the script passed to "
                          "hookutils.exec-script must be located in "
                          "the `PyInstaller/utils/hooks/subproc` directory.")

    cmd = [script_filename]
    cmd.extend(args)
    return __exec_python_cmd(cmd, env=env)


def eval_statement(statement):
    txt = exec_statement(statement).strip()
    if not txt:
        # return an empty string which is "not true" but iterable
        return ''
    return eval(txt)


def eval_script(scriptfilename, env={}, *args):
    txt = exec_script(scriptfilename, *args, env=env).strip()
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

    Let's at least try import it in a subprocess and get the difference
    in module list from sys.modules.

    This function could be used for 'hiddenimports' in PyInstaller hooks files.
    """

    statement = """
import sys
# Importing distutils filters common modules, especiall in virtualenv.
import distutils
original_modlist = set(sys.modules.keys())
# When importing this module - sys.modules gets updated.
import %(modname)s
all_modlist = set(sys.modules.keys())
diff = all_modlist - original_modlist
# Module list contain original modname. We do not need it there.
diff.discard('%(modname)s')
# Print module list to stdout.
print(list(diff))
""" % {'modname': modname}
    module_imports = eval_statement(statement)

    if not module_imports:
        logger.error('Cannot find imports for module %s' % modname)
        return []  # Means no imports found or looking for imports failed.
    #module_imports = filter(lambda x: not x.startswith('distutils'), module_imports)
    return module_imports


def qt4_plugins_dir(ns='PyQt4'):
    qt4_plugin_dirs = eval_statement(
        "from %s.QtCore import QCoreApplication;"
        "app=QCoreApplication([]);"
        # For Python 2 print would give "<PyQt4.QtCore.QStringList
        # object at 0x....>", so we need to convert each element separately
        "str=getattr(__builtins__, 'unicode', str);" # for Python 2
        "print([str(p) for p in app.libraryPaths()])" % ns)
    if not qt4_plugin_dirs:
        logger.error('Cannot find %s plugin directories' % ns)
        return ""
    for d in qt4_plugin_dirs:
        if os.path.isdir(d):
            return str(d)  # must be 8-bit chars for one-file builds
    logger.error('Cannot find existing %s plugin directory' % ns)
    return ""


def qt4_phonon_plugins_dir(ns='PyQt4'):
    qt4_plugin_dirs = eval_statement(
        "from PyQt4.QtGui import QApplication;"
        "app=QApplication([]); app.setApplicationName('pyinstaller');"
        "from PyQt4.phonon import Phonon;"
        "v=Phonon.VideoPlayer(Phonon.VideoCategory);"
        # For Python 2 print would give "<PyQt4.QtCore.QStringList
        # object at 0x....>", so we need to convert each element separately
        "str=getattr(__builtins__, 'unicode', str);" # for Python 2
        "print([str(p) for p in app.libraryPaths()])")
    if not qt4_plugin_dirs:
        logger.error("Cannot find PyQt4 phonon plugin directories")
        return ""
    for d in qt4_plugin_dirs:
        if os.path.isdir(d):
            return str(d)  # must be 8-bit chars for one-file builds
    logger.error("Cannot find existing PyQt4 phonon plugin directory")
    return ""


def qt4_plugins_binaries(plugin_type, ns='PyQt4'):
    """Return list of dynamic libraries formatted for mod.binaries."""
    pdir = qt4_plugins_dir(ns=ns)
    files = misc.dlls_in_dir(os.path.join(pdir, plugin_type))

    # Windows:
    #
    # dlls_in_dir() grabs all files ending with *.dll, *.so and *.dylib in a certain
    # directory. On Windows this would grab debug copies of Qt 4 plugins, which then
    # causes PyInstaller to add a dependency on the Debug CRT __in addition__ to the
    # release CRT.
    #
    # Since debug copies of Qt4 plugins end with "d4.dll" we filter them out of the
    # list.
    #
    if is_win:
        files = [f for f in files if not f.endswith("d4.dll")]

    dest_dir = os.path.join('qt4_plugins', plugin_type)
    binaries = [
        (f, dest_dir)
        for f in files]
    return binaries


def qt4_menu_nib_dir():
    """Return path to Qt resource dir qt_menu.nib. OSX only"""
    menu_dir = ''
    # Detect MacPorts prefix (usually /opt/local).
    # Suppose that PyInstaller is using python from macports.
    macports_prefix = os.path.realpath(sys.executable).split('/Library')[0]

    # list of directories where to look for qt_menu.nib
    dirs = []

    # Look into user-specified directory, just in case Qt4 is not installed
    # in a standard location
    if 'QTDIR' in os.environ:
        dirs += [
            os.path.join(os.environ['QTDIR'], "QtGui.framework/Versions/4/Resources"),
            os.path.join(os.environ['QTDIR'], "lib", "QtGui.framework/Versions/4/Resources"),
        ]

    # If PyQt4 is built against Qt5 look for the qt_menu.nib in a user
    # specified location, if it exists.
    if 'QT5DIR' in os.environ:
        dirs.append(os.path.join(os.environ['QT5DIR'],
                                 "src", "plugins", "platforms", "cocoa"))

    dirs += [
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

    # Qt from Homebrew
    homebrewqtpath = get_homebrew_path('qt')
    if homebrewqtpath:
        dirs.append( os.path.join(homebrewqtpath,'lib','QtGui.framework','Versions','4','Resources') )

    # Check directory existence
    for d in dirs:
        d = os.path.join(d, 'qt_menu.nib')
        if os.path.exists(d):
            menu_dir = d
            break

    if not menu_dir:
        logger.error('Cannot find qt_menu.nib directory')
    return menu_dir

def qt5_plugins_dir():
    if 'QT_PLUGIN_PATH' in os.environ and os.path.isdir(os.environ['QT_PLUGIN_PATH']):
        return str(os.environ['QT_PLUGIN_PATH'])

    qt5_plugin_dirs = eval_statement(
        "from PyQt5.QtCore import QCoreApplication;"
        "app=QCoreApplication([]);"
        # For Python 2 print would give "<PyQt4.QtCore.QStringList
        # object at 0x....>", so we need to convert each element separately
        "str=getattr(__builtins__, 'unicode', str);" # for Python 2
        "print([str(p) for p in app.libraryPaths()])")
    if not qt5_plugin_dirs:
        logger.error("Cannot find PyQt5 plugin directories")
        return ""
    for d in qt5_plugin_dirs:
        if os.path.isdir(d):
            return str(d)  # must be 8-bit chars for one-file builds
    logger.error("Cannot find existing PyQt5 plugin directory")
    return ""


def qt5_phonon_plugins_dir():
    qt5_plugin_dirs = eval_statement(
        "from PyQt5.QtGui import QApplication;"
        "app=QApplication([]); app.setApplicationName('pyinstaller');"
        "from PyQt5.phonon import Phonon;"
        "v=Phonon.VideoPlayer(Phonon.VideoCategory);"
        # For Python 2 print would give "<PyQt4.QtCore.QStringList
        # object at 0x....>", so we need to convert each element separately
        "str=getattr(__builtins__, 'unicode', str);" # for Python 2
        "print([str(p) for p in app.libraryPaths()])")
    if not qt5_plugin_dirs:
        logger.error("Cannot find PyQt5 phonon plugin directories")
        return ""
    for d in qt5_plugin_dirs:
        if os.path.isdir(d):
            return str(d)  # must be 8-bit chars for one-file builds
    logger.error("Cannot find existing PyQt5 phonon plugin directory")
    return ""


def qt5_plugins_binaries(plugin_type):
    """Return list of dynamic libraries formatted for mod.binaries."""
    pdir = qt5_plugins_dir()
    files = misc.dlls_in_dir(os.path.join(pdir, plugin_type))
    dest_dir = os.path.join('qt5_plugins', plugin_type)
    binaries = [
        (f, dest_dir)
        for f in files]
    return binaries


def qt5_menu_nib_dir():
    """Return path to Qt resource dir qt_menu.nib. OSX only"""
    menu_dir = ''

    # If the QT5DIR env var is set then look there first. It should be set to the
    # qtbase dir in the Qt5 distribution.
    dirs = []
    if 'QT5DIR' in os.environ:
        dirs.append(os.path.join(os.environ['QT5DIR'],
                                 "src", "plugins", "platforms", "cocoa"))
        dirs.append(os.path.join(os.environ['QT5DIR'],
                                 "src", "qtbase", "src", "plugins", "platforms", "cocoa"))

    # As of the time of writing macports doesn't yet support Qt5. So this is
    # just modified from the Qt4 version.
    # FIXME: update this when MacPorts supports Qt5
    # Detect MacPorts prefix (usually /opt/local).
    # Suppose that PyInstaller is using python from macports.
    macports_prefix = os.path.realpath(sys.executable).split('/Library')[0]
    # list of directories where to look for qt_menu.nib
    dirs.extend( [
        # Qt5 from MacPorts not compiled as framework.
        os.path.join(macports_prefix, 'lib', 'Resources'),
        # Qt5 from MacPorts compiled as framework.
        os.path.join(macports_prefix, 'libexec', 'qt5-mac', 'lib',
            'QtGui.framework', 'Versions', '5', 'Resources'),
        # Qt5 installed into default location.
        '/Library/Frameworks/QtGui.framework/Resources',
        '/Library/Frameworks/QtGui.framework/Versions/5/Resources',
        '/Library/Frameworks/QtGui.Framework/Versions/Current/Resources',
    ])

    # Qt5 from Homebrew
    homebrewqtpath = get_homebrew_path('qt5')
    if homebrewqtpath:
        dirs.append( os.path.join(homebrewqtpath,'src','qtbase','src','plugins','platforms','cocoa') )

    # Check directory existence
    for d in dirs:
        d = os.path.join(d, 'qt_menu.nib')
        if os.path.exists(d):
            menu_dir = d
            break

    if not menu_dir:
        logger.error('Cannot find qt_menu.nib directory')
    return menu_dir

def get_homebrew_path(formula = ''):
    '''Return the homebrew path to the requested formula, or the global prefix when
       called with no argument.  Returns the path as a string or None if not found.'''
    import subprocess
    brewcmd = ['brew','--prefix']
    path = None
    if formula:
        brewcmd.append(formula)
        dbgstr = 'homebrew formula "%s"' %formula
    else:
        dbgstr = 'homebrew prefix'
    try:
        path = subprocess.check_output(brewcmd).strip()
        logger.debug('Found %s at "%s"' % (dbgstr, path))
    except OSError:
        logger.debug('Detected homebrew not installed')
    except subprocess.CalledProcessError:
        logger.debug('homebrew formula "%s" not installed' % formula)
    if path:
        if is_py3:
            path = path.decode('utf8')  # OS X filenames are UTF-8
        return path
    else:
        return None

def get_qmake_path(version = ''):
    '''
    Try to find the path to qmake with version given by the argument
    as a string.
    '''
    import subprocess

    # Use QT[45]DIR if specified in the environment
    if 'QT5DIR' in os.environ and version[0] == '5':
        logger.debug('Using $QT5DIR/bin as qmake path')
        return os.path.join(os.environ['QT5DIR'],'bin','qmake')
    if 'QT4DIR' in os.environ and version[0] == '4':
        logger.debug('Using $QT4DIR/bin as qmake path')
        return os.path.join(os.environ['QT4DIR'],'bin','qmake')

    # try the default $PATH
    dirs = ['']

    # try homebrew paths
    for formula in ('qt','qt5'):
        homebrewqtpath = get_homebrew_path(formula)
        if homebrewqtpath:
            dirs.append(homebrewqtpath)

    for dir in dirs:
        try:
            qmake = os.path.join(dir, 'qmake')
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
       qmldir = compat.exec_command(qmake, "-query", "QT_INSTALL_QML").strip()
    if len(qmldir) == 0:
        logger.error('Cannot find QT_INSTALL_QML directory, "qmake -query '
                        + 'QT_INSTALL_QML" returned nothing')
    elif not os.path.exists(qmldir):
        logger.error("Directory QT_INSTALL_QML: %s doesn't exist" % qmldir)

    # 'qmake -query' uses / as the path separator, even on Windows
    qmldir = os.path.normpath(qmldir)
    return qmldir

def qt5_qml_data(dir):
    """Return Qml library dir formatted for data"""
    qmldir = qt5_qml_dir()
    return (os.path.join(qmldir, dir), 'qml')

def qt5_qml_plugins_binaries(dir):
    """Return list of dynamic libraries formatted for mod.binaries."""
    binaries = []
    qmldir = qt5_qml_dir()
    files = misc.dlls_in_subdirs(os.path.join(qmldir, dir))
    for f in files:
        relpath = os.path.relpath(f, qmldir)
        instdir, file = os.path.split(relpath)
        instdir = os.path.join("qml", instdir)
        logger.debug("qt5_qml_plugins_binaries installing %s in %s"
                     % (f, instdir) )
        binaries.append((f, instdir))
    return binaries


def django_dottedstring_imports(django_root_dir):
    """
    Get all the necessary Django modules specified in settings.py.

    In the settings.py the modules are specified in several variables
    as strings.
    """
    pths = []
    # Extend PYTHONPATH with parent dir of django_root_dir.
    pths.append(misc.get_path_to_toplevel_modules(django_root_dir))
    # Extend PYTHONPATH with django_root_dir.
    # Many times Django users do not specify absolute imports in the settings module.
    pths.append(django_root_dir)

    package_name = os.path.basename(django_root_dir) + '.settings'
    env = {'DJANGO_SETTINGS_MODULE': package_name,
           'PYTHONPATH': os.pathsep.join(pths)}
    ret = eval_script('django_import_finder.py', env=env)

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
    from PyInstaller.config import CONF
    manage_py = CONF['main_script']
    manage_dir = os.path.dirname(os.path.abspath(manage_py))

    # Get the Django root directory. The directory that contains settings.py and url.py.
    # It could be the directory containig manage.py or any of its subdirectories.
    settings_dir = None
    files = set(os.listdir(manage_dir))
    if 'settings.py' in files and 'urls.py' in files:
        settings_dir = manage_dir
    else:
        for f in files:
            if os.path.isdir(os.path.join(manage_dir, f)):
                subfiles = os.listdir(os.path.join(manage_dir, f))
                # Subdirectory contains critical files.
                if 'settings.py' in subfiles and 'urls.py' in subfiles:
                    settings_dir = os.path.join(manage_dir, f)
                    break  # Find the first directory.

    return settings_dir


# TODO Move to "hooks/hook-OpenGL.py", the only place where this is called.
def opengl_arrays_modules():
    """
    Return list of array modules for OpenGL module.

    e.g. 'OpenGL.arrays.vbo'
    """
    statement = 'import OpenGL; print(OpenGL.__path__[0])'
    opengl_mod_path = exec_statement(statement)
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
    This function removes the given prefix from a string, if the string does
    indeed begin with the prefix; otherwise, it returns the string
    unmodified.
    """
    if string.startswith(prefix):
        return string[len(prefix):]
    else:
        return string


def remove_suffix(string, suffix):
    """
    This function removes the given suffix from a string, if the string
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
    This function returns filename without its extension.
    """
    return os.path.splitext(filename)[0]


def get_module_file_attribute(package):
    """
    Get the absolute path of the module with the passed name.

    Since modules *cannot* be directly imported during analysis, this function
    spawns a subprocess importing this module and returning the value of this
    module's `__file__` attribute.

    Parameters
    ----------
    module_name : str
        Fully-qualified name of this module.

    Returns
    ----------
    str
        Absolute path of this module.
    """
    # First try to use 'pkgutil'. - fastest but doesn't work on
    # certain modules in pywin32, which replace all module attributes
    # with those of the .dll
    try:
        loader = pkgutil.find_loader(package)
        attr = loader.get_filename(package)
    # Second try to import module in a subprocess. Might raise ImportError.
    except (AttributeError, ImportError):
        # Statement to return __file__ attribute of a package.
        __file__statement = """
import %s as p
print(p.__file__)
"""
        attr = exec_statement(__file__statement % package)
        if not attr.strip():
            raise ImportError
    return attr



def get_pywin32_module_file_attribute(module_name):
    """
    Get the absolute path of the PyWin32 module with the passed name.

    Parameters
    ----------
    module_name : str
        Fully-qualified name of this module.

    Returns
    ----------
    str
        Absolute path of this module.

    See Also
    ----------
    `PyInstaller.utils.win32.winutils.import_pywin32_module()`
        For further details.
    """
    # On import, the pywin32 module imports a DLL and replaces all its attributes with
    # those from the DLL, and also replaces its __file__.
    # Execute module in subprocess to get actual __file__ of the DLL.

    # NOTE: get_pywin32_module_file_attribute requires PyInstaller to be on the default
    # sys.path for the called python process. Running py.test changes the working dir
    # to a temp dir, so PyInstaller should be installed via setup.py install or
    # setup.py develop before running py.test.


    statement = """
from PyInstaller.utils.win32 import winutils
module = winutils.import_pywin32_module('%s')
print(module.__file__)
"""
    return exec_statement(statement % module_name)


def is_module_version(module_name, comparison_name, module_version):
    """
    Check the version of the module with the passed name against the passed
    version string using the comparison operator with the passed name.

    This function provides robust version checking based on the same low-level
    algorithm leveraged by both `easy_install` and `pip`, and should _always_ be
    called in lieu of manually comparing version strings. In particular, version
    strings should _never_ be compared lexicographically (e.g., `'00.5' > '0.6'`
    is technically `True`, despite being semantically untrue).

    The passed module name should be a fully-qualified `.`-delimited module name
    (e.g., `PyInstaller.util`). The passed version string should be a PEP
    0440-compliant `.`-delimited version specifier (e.g., `3.14-rc5`). The
    passed comparison name should be one of the following eight strings:

    * '>=' or 'ge', performing a greater-than-or-equal-to comparison.
    * '<=' or 'le', performing a less-than-or-equal-to comparison.
    * '>' or 'gt', performing a greater-than comparison.
    * '<' or 'lt', performing a less-than comparison.

    Implementation
    ----------
    Specifically, this function:

    . Spawns a subprocess importing this module and getting the value of this
      module's `__version__` attribute.
    . Converts both that value and the passed version string to comparable
      tuples via the `pkg_resources.parse_version()` `setuptools` function.
    . Returns the boolean returned by dynamically calling the private method of
      the first such tuple corresponding to the passed comparison operator name
      (e.g., the `tuple.__lt__()` method if that name is either `<` or `lt`),
      passed the second such tuple.

    Note that `pkg_resources.parse_version()` is generally considered to be the
    most robust means of comparing version strings in Python. The
    alternative `LooseVersion()` and `StrictVersion()` functions provided by the
    standard `distutils.version` module fail for common edge-cases: e.g.,

        >>> from distutils.version import LooseVersion
        >>> LooseVersion('1.5') >= LooseVersion('1.5-rc2')
        False
        >>> from pkg_resources import parse_version
        >>> parse_version('1.5') >= parse_version('1.5-rc2')
        True

    Parameters
    ----------
    module_name : str
        Fully-qualified `.`-delimited module name.
    comparison_name : str
        Either '>=', 'ge', '<=', 'le', '>', 'gt', '<', or 'lt'.
    module_version : str
        PEP 0440-compliant `.`-delimited version specifier.

    Returns
    ----------
    bool
        Boolean returned by performing the desired module version check.

    Examples
    ----------
        # Test whether the local version of Sphinx is 1.3.x or newer.
        >>> from PyInstaller.utils.hooks.hookutils import is_module_version
        >>> is_module_version('sphinx', '>=', '1.3.1')
        True
    """
    # Dictionary mapping passed comparison names to private tuple method names.
    comparison_to_method_name = {
        '>=': '__ge__',
        'ge': '__ge__',
        '<=': '__le__',
        'le': '__le__',
        '>':  '__gt__',
        'gt': '__gt__',
        '<':  '__lt__',
        'lt': '__lt__',
    }

    # If the passed comparison name is unrecognized, raise an exception.
    if comparison_name not in comparison_to_method_name:
        raise KeyError('Comparison name "%s" unrecognized.' % comparison_name)

    # String module version obtained by importing this module in a subprocess.
    statement = """
import %s as module
print(module.__version__)
"""
    module_version_real = exec_statement(statement % module_name)

    # Convert incomparable version strings to comparable version tuples.
    module_version_real_tuple = pkg_resources.parse_version(module_version_real)
    module_version_fake_tuple = pkg_resources.parse_version(module_version)

    # Private tuple method performing this comparison.
    module_version_real_tuple_comparator = getattr(
        module_version_real_tuple, comparison_to_method_name[comparison_name])

    # Finally, compare the two versions.
    return module_version_real_tuple_comparator(module_version_fake_tuple)


def is_package(module_name):
    """
    Check if a Python module is really a module or is a package containing
    other modules.

    :param module_name: Module name to check.
    :return: True if module is a package else otherwise.
    """
    # This way determines if module is a package without importing the module.
    try:
        loader = pkgutil.find_loader(module_name)
    except Exception:
        # When it fails to find a module loader then it points probably to a clas
        # or function and module is not a package. Just return False.
        return False
    else:
        if loader:
            # A package must have a __path__ attribute.
            return loader.is_package(module_name)
        else:
            # In case of None - modules is probably not a package.
            return False


def get_package_paths(package):
    """
    Given a package, return the path to packages stored on this machine
    and also returns the path to this particular package. For example,
    if pkg.subpkg lives in /abs/path/to/python/libs, then this function
    returns (/abs/path/to/python/libs,
             /abs/path/to/python/libs/pkg/subpkg).
    """
    file_attr = get_module_file_attribute(package)

    # package.__file__ = /abs/path/to/package/subpackage/__init__.py.
    # Search for Python files in /abs/path/to/package/subpackage; pkg_dir
    # stores this path.
    pkg_dir = os.path.dirname(file_attr)
    # When found, remove /abs/path/to/ from the filename; pkg_base stores
    # this path to be removed.
    pkg_base = remove_suffix(pkg_dir, package.replace('.', os.sep))

    return pkg_base, pkg_dir


def collect_submodules(package, subdir=None, pattern=None):
    """
    The following two functions were originally written by Ryan Welsh
    (welchr AT umich.edu).

    :param pattern: String pattern to match only submodules containing
                    this pattern in the name.

    This produces a list of strings which specify all the modules in
    package.  Its results can be directly assigned to ``hiddenimports``
    in a hook script; see, for example, hook-sphinx.py. The
    package parameter must be a string which names the package. The
    optional subdir give a subdirectory relative to package to search,
    which is helpful when submodules are imported at run-time from a
    directory lacking __init__.py. See hook-astroid.py for an example.

    This function does not work on zipped Python eggs.

    This function is used only for hook scripts, but not by the body of
    PyInstaller.
    """
    # Accept only strings as packages.
    if type(package) is not str:
        raise ValueError

    logger.debug('Collecting submodules for %s' % package)
    # Skip module that is not a package.
    if not is_package(package):
        logger.debug('collect_submodules: Module %s is not a package.' % package)
        return []

    pkg_base, pkg_dir = get_package_paths(package)
    if subdir:
        pkg_dir = os.path.join(pkg_dir, subdir)
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
                    extension in PY_EXECUTABLE_SUFFIXES):
                    modname = mod_path + "." + remove_file_extension(f)
                    # TODO convert this into regex matching.
                    # Skip submodules not matching pattern.
                    if pattern and not pattern in modname:
                        continue
                    mods.add(modname)
        else:
        # If not, nothing here is part of the package; don't visit any of
        # these subdirs.
            del dirnames[:]

    return list(mods)


# Patterns of dynamic library filenames that might be bundled with some
# installed Python packages.
PY_DYLIB_PATTERNS = [
    '*.dll',
    '*.dylib',
    # Some packages contain dynamic libraries that ends with the same
    # suffix as Python C extensions. E.g. zmq:  libzmq.pyd, libsodium.pyd.
    # Those files usually starts with 'lib' prefix.
    'lib*.pyd',
    'lib*.so',
]


def collect_dynamic_libs(package):
    """
    This routine produces a list of (source, dest) of dynamic library
    files which reside in package. Its results can be directly assigned to
    ``binaries`` in a hook script; see, for example, hook-zmq.py. The
    package parameter must be a string which names the package.
    """
    # Accept only strings as packages.
    if type(package) is not str:
        raise ValueError

    logger.debug('Collecting dynamic libraries for %s' % package)
    pkg_base, pkg_dir = get_package_paths(package)
    # Walk through all file in the given package, looking for dynamic libraries.
    dylibs = []
    for dirpath, _, __ in os.walk(pkg_dir):
        # Try all file patterns in a given directory.
        for pattern in PY_DYLIB_PATTERNS:
            files = glob.glob(os.path.join(dirpath, pattern))
            for source in files:
                # Produce the tuple
                # (/abs/path/to/source/mod/submod/file.pyd,
                #  mod/submod/file.pyd)
                dest = remove_prefix(dirpath, os.path.dirname(pkg_base) + os.sep)
                logger.debug(' %s, %s' % (source, dest))
                dylibs.append((source, dest))
    return dylibs


def collect_data_files(package, include_py_files=False, subdir=None):
    """
    This routine produces a list of (source, dest) non-Python (i.e. data)
    files which reside in package. Its results can be directly assigned to
    ``datas`` in a hook script; see, for example, hook-sphinx.py. The
    package parameter must be a string which names the package.
    By default, all Python executable files (those ending in .py, .pyc,
    and so on) will NOT be collected; setting the include_py_files
    argument to True collects these files as well. This is typically used
    with Python routines (such as those in pkgutil) that search a given
    directory for Python executable files then load them as extensions or
    plugins. See collect_submodules for a description of the subdir parameter.

    This function does not work on zipped Python eggs.

    This function is used only for hook scripts, but not by the body of
    PyInstaller.
    """
    # Accept only strings as packages.
    if type(package) is not str:
        raise ValueError

    pkg_base, pkg_dir = get_package_paths(package)
    if subdir:
        pkg_dir = os.path.join(pkg_dir, subdir)
    # Walk through all file in the given package, looking for data files.
    datas = []
    for dirpath, dirnames, files in os.walk(pkg_dir):
        for f in files:
            extension = os.path.splitext(f)[1]
            if include_py_files or (not extension in PY_IGNORE_EXTENSIONS):
                # Produce the tuple
                # (/abs/path/to/source/mod/submod/file.dat,
                #  mod/submod/file.dat)
                source = os.path.join(dirpath, f)
                dest = remove_prefix(dirpath,
                                     os.path.dirname(pkg_base) + os.sep)
                datas.append((source, dest))

    return datas


def _find_prefix(filename):
    """
    In virtualenv, _CONFIG_H and _MAKEFILE may have same or different
    prefixes, depending on the version of virtualenv.
    Try to find the correct one, which is assumed to be the longest one.
    """
    if not compat.is_venv:
        return sys.prefix
    prefixes = [os.path.abspath(sys.prefix), compat.base_prefix]
    possible_prefixes = []
    for prefix in prefixes:
        common = os.path.commonprefix([prefix, filename])
        if common == prefix:
            possible_prefixes.append(prefix)
    possible_prefixes.sort(key=lambda p: len(p), reverse=True)
    return possible_prefixes[0]

def relpath_to_config_or_make(filename):
    """
    The following is refactored out of hook-sysconfig and hook-distutils,
    both of which need to generate "datas" tuples for pyconfig.h and
    Makefile, under the same conditions.
    """

    # Relative path in the dist directory.
    prefix = _find_prefix(filename)
    return os.path.relpath(os.path.dirname(filename), prefix)


def get_typelibs(module, version):
    datas = []
    statement = """
import gi
gi.require_version("GIRepository", "2.0")
from gi.repository import GIRepository
print(GIRepository.Repository.get_search_path())"""
    typelibs_path = eval_statement(statement)[0]
    pattern = os.path.join(typelibs_path, module + '*' + version + '*')
    for f in glob.glob(pattern):
        d = gir_library_path_fix(f)
        if d:
            datas.append(d)
    return datas


def gir_library_path_fix(path):
    import subprocess

    path = os.path.abspath(path)
    common_path = os.path.commonprefix([sys.prefix, path])
    gir_path = os.path.join(common_path, 'share', 'gir-1.0')

    typelib_name = os.path.basename(path)
    gir_name = os.path.splitext(typelib_name)[0] + '.gir'

    gir_file = os.path.join(gir_path, gir_name)

    if is_darwin:
        if not os.path.exists(gir_path):
            logger.error('Unable to find gir directory: %s.\n'
                         'Try installing your platforms gobject-introspection '
                         'package.', gir_path)
            return None
        if not os.path.exists(gir_file):
            logger.error('Unable to find gir file: %s.\n'
                         'Try installing your platforms gobject-introspection '
                         'package.', gir_file)
            return None

        with open(gir_file, 'r') as f:
            lines = f.readlines()
        with open(os.path.join(CONF['workpath'], gir_name), 'w') as f:
            for line in lines:
                if 'shared-library' in line:
                    split = re.split('(=)', line)
                    files = re.split('(["|,])', split[2])
                    for count, item in enumerate(files):
                        if 'lib' in item:
                            files[count] = '@loader_path/' + os.path.basename(item)
                    line = ''.join(split[0:2]) + ''.join(files)
                f.write(line)

        # g-ir-compiler expects a file so we cannot just pipe the fixed file to it.
        command = subprocess.Popen(('g-ir-compiler', os.path.join(CONF['workpath'], gir_name),
                                    '-o', os.path.join(CONF['workpath'], typelib_name)))
        command.wait()

        return (os.path.join(CONF['workpath'], typelib_name), 'gi_typelibs')
    else:
        return (path, 'gi_typelibs')
