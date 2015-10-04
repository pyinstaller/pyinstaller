#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Various classes and functions to provide some backwards-compatibility
with previous versions of Python from 2.7 onward.
"""


import os
import platform
import site
import subprocess
import sys


# Distinguish code for different major Python version.
is_py2 = sys.version_info[0] == 2
is_py3 = sys.version_info[0] == 3
# Distinguish specific code for various Python versions.
is_py27 = sys.version_info >= (2, 7) and sys.version_info < (3, 0)
# PyInstaller supports only Python 3.3+
# Variables 'is_pyXY' mean that Python X.Y and up is supported.
is_py34 = sys.version_info >= (3, 4)
is_py35 = sys.version_info >= (3, 5)
is_py36 = sys.version_info >= (3, 6)

is_win = sys.platform.startswith('win')
is_cygwin = sys.platform == 'cygwin'
is_darwin = sys.platform == 'darwin'  # Mac OS X

# Unix platforms
is_linux = sys.platform.startswith('linux')
is_solar = sys.platform.startswith('sun')  # Solaris
is_aix = sys.platform.startswith('aix')
is_freebsd = sys.platform.startswith('freebsd')

# Some code parts are similar to several unix platforms
# (e.g. Linux, Solaris, AIX)
# Mac OS X is not considered as unix since there are many
# platform specific details for Mac in PyInstaller.
is_unix = is_linux or is_solar or is_aix or is_freebsd


# On different platforms is different file for dynamic python library.
_pyver = sys.version_info[:2]
if is_win:
    PYDYLIB_NAMES = set(['python%d%d.dll' % _pyver])
elif is_cygwin:
    PYDYLIB_NAMES = set(['libpython%d%d.dll' % _pyver])
elif is_darwin:
    PYDYLIB_NAMES = set(['Python', '.Python', 'libpython%d.%d.dylib' % _pyver])
elif is_aix:
    # Shared libs on AIX are archives with shared object members, thus the ".a" suffix.
    PYDYLIB_NAMES = set(['libpython%d.%d.a' % _pyver])
elif is_freebsd:
    PYDYLIB_NAMES = set(['libpython%d.%d.so.1' % _pyver,
                         'libpython%d.%dm.so.1' % _pyver,
                         'libpython%d.%d.so.1.0' % _pyver,
                         'libpython%d.%dm.so.1.0' % _pyver])
elif is_unix:
    # Other *nix platforms.
    # Python 2 .so library on Linux is: libpython2.7.so.1.0
    # Python 3 .so library on Linux is: libpython3.2mu.so.1.0, libpython3.3m.so.1.0
    PYDYLIB_NAMES = set(['libpython%d.%d.so.1.0' % _pyver,
                         'libpython%d.%dm.so.1.0' % _pyver,
                         'libpython%d.%dmu.so.1.0' % _pyver])
else:
    raise SystemExit('Your platform is not yet supported. '
                     'Please define constant PYDYLIB_NAMES for your platform.')


# In Python 3 there is exception FileExistsError. But it is not available
# in Python 2. For Python 2 fall back to OSError exception.
if is_py2:
    FileExistsError = OSError
else:
    from builtins import FileExistsError


# In Python 3 built-in function raw_input() was renamed to just 'input()'.
try:
    stdin_input = raw_input
except NameError:
    stdin_input = input

# Safe repr that always outputs ascii

if is_py2:
    safe_repr = repr
else:
    safe_repr = ascii

# UserList class is moved to 'collections.UserList in Python 3.
try:
    from collections import UserList
except ImportError:
    from UserList import UserList

# UserDict class is moved to 'collections.UserDict in Python 3.
try:
    from collections import UserDict
except ImportError:
    # PyInstaller needs iterable dist  'for a in dict'
    from UserDict import IterableUserDict as UserDict


# Correct extension ending: 'c' or 'o'
if __debug__:
    PYCO = 'c'
else:
    PYCO = 'o'


# Obsolete command line options (do not exist anymore).
_OLD_OPTIONS = [
    '--upx', '-X',
    '-K', '--tk',
    '-C', '--configfile',
    '--skip-configure',
    '-o', '--out',
    '--buildpath',
    ]


# Options for python interpreter when invoked in a subprocess.
if __debug__:
    # Python started *without* -O
    _PYOPTS = ''
else:
    _PYOPTS = '-O'


# In a virtual environment created by virtualenv (github.com/pypa/virtualenv)
# there exists sys.real_prefix with the path to the base Python
# installation from which the virtual environment was created. This is true regardless of
# the version of Python used to execute the virtualenv command, 2.x or 3.x.
#
# In a virtual environment created by the venv module available in
# the Python 3 standard lib, there exists sys.base_prefix with the path to
# the base implementation. This does not exist in Python 2.x or in
# a virtual environment created by virtualenv.
#
# The following code creates compat.is_venv and is.virtualenv
# that are True when running a virtual environment, and also
# compat.base_prefix with the path to the
# base Python installation.

base_prefix = getattr( sys, 'real_prefix',
                       getattr( sys, 'base_prefix', sys.prefix )
                        )
is_venv = is_virtualenv = base_prefix != sys.prefix


# In Python 3.4 module 'imp' is deprecated and there is another way how
# to obtain magic value.
if is_py34:
    import importlib.util
    BYTECODE_MAGIC = importlib.util.MAGIC_NUMBER
else:
    # This fallback should work with Python 2.7 and 3.3.
    import imp
    BYTECODE_MAGIC = imp.get_magic()


# List of suffixes for Python C extension modules.
try:
    # In Python 3.3+ There is a list
    from importlib.machinery import EXTENSION_SUFFIXES
except ImportError:
    import imp
    EXTENSION_SUFFIXES = [f[0] for f in imp.get_suffixes()
                          if f[2] == imp.C_EXTENSION]


# In Python 3 'Tkinter' has been made lowercase - 'tkinter'. Keep Python 2
# compatibility.
if is_py2:
    modname_tkinter = 'Tkinter'
else:
    modname_tkinter = 'tkinter'


def architecture():
    """
    Returns the bit depth of the python interpreter's architecture as
    a string ('32bit' or '64bit'). Similar to platform.architecture(),
    but with fixes for universal binaries on MacOS.
    """
    if is_darwin:
        # Darwin's platform.architecture() is buggy and always
        # returns "64bit" event for the 32bit version of Python's
        # universal binary. So we roll out our own (that works
        # on Darwin).
        if sys.maxsize > 2 ** 32:
            return '64bit'
        else:
            return '32bit'
    else:
        return platform.architecture()[0]


def system():
    # On some Windows installation (Python 2.4) platform.system() is
    # broken and incorrectly returns 'Microsoft' instead of 'Windows'.
    # http://mail.python.org/pipermail/patches/2007-June/022947.html
    syst = platform.system()
    if syst == 'Microsoft':
        return 'Windows'
    return syst


def machine():
    """
    Return machine suffix to use in directory name when looking
    for bootloader.

    PyInstaller is reported to work even on ARM architecture. For that
    case functions system() and architecture() are not enough.
    Path to bootloader has to be composed from system(), architecture()
    and machine() like:
        'Linux-32bit-arm'
    """
    mach = platform.machine()
    if mach.startswith('arm'):
        return 'arm'
    else:
        # Assume x86/x86_64 machine.
        return None


# Set and get environment variables does not handle unicode strings correctly
# on Windows.

# Acting on os.environ instead of using getenv()/setenv()/unsetenv(),
# as suggested in <http://docs.python.org/library/os.html#os.environ>:
# "Calling putenv() directly does not change os.environ, so it's
# better to modify os.environ." (Same for unsetenv.)

def getenv(name, default=None):
    """
    Returns unicode string containing value of environment variable 'name'.
    """
    return os.environ.get(name, default)


def setenv(name, value):
    """
    Accepts unicode string and set it as environment variable 'name' containing
    value 'value'.
    """
    os.environ[name] = value


def unsetenv(name):
    """
    Delete the environment variable 'name'.
    """
    # Some platforms (e.g. AIX) do not support `os.unsetenv()` and
    # thus `del os.environ[name]` has no effect onto the real
    # environment. For this case we set the value to the empty string.
    os.environ[name] = ""
    del os.environ[name]


# Exec commands in subprocesses.


def exec_command(*cmdargs, **kwargs):
    """
    Wrap creating subprocesses

    Return stdout of the invoked command. On Python 3, the 'encoding' kwarg controls
    how the output is decoded to 'str'
    """
    encoding = kwargs.pop('encoding', None)
    out = subprocess.Popen(cmdargs, stdout=subprocess.PIPE, **kwargs).communicate()[0]
    # Python 3 returns stdout/stderr as a byte array NOT as string.
    # Thus we need to convert that to proper encoding.

    if is_py3:
        if encoding:
            out = out.decode(encoding)
        else:
            # If no encoding is given, assume we're reading filenames from stdout
            # only because it's the common case.
            out = os.fsdecode(out)

    return out


def exec_command_rc(*cmdargs, **kwargs):
    """
    Wrap creating subprocesses.

    Return exit code of the invoked command.
    """
    # 'encoding' keyword is not supported for 'subprocess.call'.
    # Remove it thus from kwargs.
    if 'encoding' in kwargs:
        kwargs.pop('encoding')
    return subprocess.call(cmdargs, **kwargs)


def exec_command_all(*cmdargs, **kwargs):
    """
    Wrap creating subprocesses

    Return tuple (exit_code, stdout, stderr) of the invoked command.

    On Python 3, the 'encoding' kwarg controls how stdout and stderr are decoded to 'str'
    """
    proc = subprocess.Popen(cmdargs, bufsize=-1,  # Default OS buffer size.
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
    # Waits for subprocess to complete.
    out, err = proc.communicate()
    # Python 3 returns stdout/stderr as a byte array NOT as string.
    # Thus we need to convert that to proper encoding.
    if is_py3:
        encoding = kwargs.get('encoding')
        if encoding:
            out = out.decode(encoding)
            err = err.decode(encoding)
        else:
            # If no encoding is given, assume we're reading filenames from stdout
            # only because it's the common case.
            out = os.fsdecode(out)
            err = os.fsdecode(err)


    return proc.returncode, out, err


def __wrap_python(args, kwargs):
    cmdargs = [sys.executable]

    # Mac OS X supports universal binaries (binary for multiple architectures.
    # We need to ensure that subprocess binaries are running for the same
    # architecture as python executable.
    # It is necessary to run binaries with 'arch' command.
    if is_darwin:
        mapping = {'32bit': '-i386', '64bit': '-x86_64'}
        py_prefix = ['arch', mapping[architecture()]]
        cmdargs = py_prefix + cmdargs

    if _PYOPTS:
        cmdargs.append(_PYOPTS)

    cmdargs.extend(args)

    env = kwargs.get('env')
    if env is None:
        env = dict(**os.environ)

    if is_py3:
        # Ensure python 3 subprocess writes 'str' as utf-8
        env['PYTHONIOENCODING'] = 'UTF-8'
        # ... and ensure we read output as utf-8
        kwargs['encoding'] = 'UTF-8'
     
    return cmdargs, kwargs


def exec_python(*args, **kwargs):
    """
    Wrap running python script in a subprocess.

    Return stdout of the invoked command.
    """
    cmdargs, kwargs = __wrap_python(args, kwargs)
    return exec_command(*cmdargs, **kwargs)


def exec_python_rc(*args, **kwargs):
    """
    Wrap running python script in a subprocess.

    Return exit code of the invoked command.
    """
    cmdargs, kwargs = __wrap_python(args, kwargs)
    return exec_command_rc(*cmdargs, **kwargs)


def exec_python_all(*args, **kwargs):
    """
    Wrap running python script in a subprocess.

    Return tuple (exit_code, stdout, stderr) of the invoked command.
    """
    cmdargs, kwargs = __wrap_python(args, kwargs)
    return exec_command_all(*cmdargs, **kwargs)


# The function os.getcwd() in Python 2 does not work with unicode paths on Windows.
def getcwd():
    """
    Wrap os.getcwd()

    On Windows return ShortPathName (8.3 filename) that contain only ascii
    characters.
    """
    cwd = os.getcwd()
    # os.getcwd works properly with Python 3 on Windows.
    # We need this workaround only for Python 2 on Windows.
    if is_win and is_py2:
        try:
            unicode(cwd)
        except UnicodeDecodeError:
            # Do conversion to ShortPathName really only in case 'cwd' is not
            # ascii only - conversion to unicode type cause this unicode error.
            try:
                import win32api
                cwd = win32api.GetShortPathName(cwd)
            except ImportError:
                pass
    return cwd


def expand_path(path):
    """
    Replace initial tilde '~' in path with user's home directory and also
    expand environment variables (${VARNAME} - Unix, %VARNAME% - Windows).
    """
    return os.path.expandvars(os.path.expanduser(path))


# Obsolete command line options.


def __obsolete_option(option, opt, value, parser):
    parser.error('%s option does not exist anymore (obsolete).' % opt)


def __add_obsolete_options(parser):
    """
    Add the obsolete options to a option-parser instance and
    print error message when they are present.
    """
    g = parser.add_option_group('Obsolete options (not used anymore)')
    g.add_option(*_OLD_OPTIONS,
                 **{'action': 'callback',
                    'callback': __obsolete_option,
                    'help': 'These options do not exist anymore.'})


# Site-packages functions - use native function if available.
if hasattr(site, 'getsitepackages'):
    getsitepackages = site.getsitepackages
# Backported For Python 2.6 and virtualenv.
# Module 'site' in virtualenv might not have this attribute.
else:
    def getsitepackages():
        """
        Return only one item as list with one item.
        """
        # For now used only on Windows. Raise Exception for other platforms.
        if is_win:
            pths = [os.path.join(sys.prefix, 'Lib', 'site-packages')]
            # Include Real sys.prefix for virtualenv.
            if is_virtualenv:
                pths.append(os.path.join(base_prefix, 'Lib', 'site-packages'))
            return pths
        else:
            # TODO Implement for Python 2.6 on other platforms.
            raise NotImplementedError()


# Function to reload a module - used to reload module 'PyInstaller.config' for tests.
# imp module is deprecated since Python 3.4.
try:
    from importlib import reload as module_reload
except ImportError:
    from imp import reload as module_reload


# Wrapper to load a module from a Python source file.
# This function loads import hooks when processing them.
if is_py2:
    import imp
    importlib_load_source = imp.load_source
else:
    import importlib.machinery
    def importlib_load_source(name, pathname):                # Import module from a file.
        mod_loader = importlib.machinery.SourceFileLoader(name, pathname)
        return mod_loader.load_module()


try:
    # new in Python 3
    FileNotFoundError_ = FileNotFoundError
except NameError:
    class FileNotFoundError(OSError):
        pass
else:
    FileNotFoundError = FileNotFoundError_
    del FileNotFoundError_


# Patterns of module names that should be bundled into the base_library.zip.
if is_py34:
    PY3_BASE_MODULES = set([
        # Py_Initialize() function uses module '_bootlocale' to set default stdout/err encodings.
        # Python 3.4
        # Module _bootlocale is just subset of 'locale' for starting Python interpreter.
        # More info: https://bugs.python.org/issue9548i
        '_bootlocale',
        '_weakrefset',
        'abc',
        'codecs',
        'encodings',
        'io',  # The 'io' module requires to set stdout/stderr encodings.
    ])
else:
    PY3_BASE_MODULES = set([
        # Python 3.3
        # The _bootlocale module is not available in Python 3.3 and whole 'locale' and its
        # dependencies have to be in base_library.zip.
        '_weakrefset',
        'abc',
        'codecs',
        'collections',
        'copyreg',
        'encodings',
        'functools',
        'io',
        'heapq',
        'keyword',
        'locale',
        're',
        'reprlib',
        'sre_compile',
        'sre_constants',
        'sre_parse',
        'weakref',
    ])

# Object types of Pure Python modules in modulegraph dependency graph.
# Pure Python modules have code object (attribute co_code).
PURE_PYTHON_MODULE_TYPES = set([
    'SourceModule',
    'CompiledModule',
    'Package',
    'NamespacePackage',
    # Deprecated.
    # TODO Could these module types be removed?
    'FlatPackage',
    'ArchiveModule',
])
# Object types of special Python modules (built-in, run-time, namespace package)
# in modulegraph dependency graph that do not have code object.
SPECIAL_MODULE_TYPES = set([
    'AliasNode',
    'BuiltinModule',
    'RuntimeModule',
    # PyInstaller handles scripts differently and not as standard Python modules.
    'Script',
])
# Object types of Binary Python modules (extensions, etc) in modulegraph
# dependency graph.
BINARY_MODULE_TYPES = set([
    'Extension',
])
# Object types of valid Python modules in modulegraph dependency graph.
VALID_MODULE_TYPES = PURE_PYTHON_MODULE_TYPES | SPECIAL_MODULE_TYPES | BINARY_MODULE_TYPES
# Object types of bad/missing/invalid Python modules in modulegraph
# dependency graph.
# TODO Should be 'Invalid' module types also in the 'MISSING' set?
BAD_MODULE_TYPES = set([
    'BadModule',
    'ExcludedModule',
    'InvalidSourceModule',
    'InvalidCompiledModule',
    'MissingModule',
])
ALL_MODULE_TYPES = VALID_MODULE_TYPES | BAD_MODULE_TYPES
# TODO Review this mapping to TOC, remove useless entries.
# Dict to map ModuleGraph node types to TOC typecodes
MODULE_TYPES_TO_TOC_DICT = {
    # Pure modules.
    'AliasNode': 'PYMODULE',
    'Script': 'PYSOURCE',
    'RuntimeModule': 'PYMODULE',
    'SourceModule': 'PYMODULE',
    'CompiledModule': 'PYMODULE',
    'Package': 'PYMODULE',
    # Binary modules.
    'Extension': 'EXTENSION',
    # Special valid modules.
    'BuiltinModule': 'BUILTIN',
    'NamespacePackage': 'PYMODULE',
    # Bad modules.
    'BadModule': 'bad',
    'ExcludedModule': 'excluded',
    'InvalidSourceModule': 'invalid',
    'InvalidCompiledModule': 'invalid',
    'MissingModule': 'missing',
    # Other.
    'FlatPackage': 'PYMODULE',
    'ArchiveModule': 'PYMODULE',
    'does not occur': 'BINARY',
}


def check_requirements():
    """
    Verify that all requirements to run PyInstaller are met. Especially
    PyWin32 is installed on Windows.

    Fail hard if any requirement is not met.
    """
    # Fail hard if Python does not have minimum required version
    if sys.version_info < (3, 3) and sys.version_info[:2] != (2, 7):
        raise SystemExit('PyInstaller requires at least Python 2.7 or 3.3+.')

    if is_win:
        try:
            from PyInstaller.utils.win32 import winutils
            pywintypes = winutils.import_pywin32_module('pywintypes')
        except ImportError:
            raise SystemExit('PyInstaller cannot check for assembly dependencies.\n'
                             'Please install PyWin32.\n\n'
                             'pip install pypiwin32\n')
