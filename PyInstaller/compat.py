#-----------------------------------------------------------------------------
# Copyright (c) 2005-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------


"""
Various classes and functions to provide some backwards-compatibility
with previous versions of Python onward.
"""

import io
import os
import platform
import site
import subprocess
import sys
import errno
from .exceptions import ExecCommandFailed

# Copied from https://docs.python.org/3/library/platform.html#cross-platform.
is_64bits = sys.maxsize > 2**32

# Distinguish specific code for various Python versions.
# Variables 'is_pyXY' mean that Python X.Y and up is supported.
# Keep even unsupported versions here to keep 3rd-party hooks working.
is_py35 = sys.version_info >= (3, 5)
is_py36 = sys.version_info >= (3, 6)
is_py37 = sys.version_info >= (3, 7)

is_win = sys.platform.startswith('win')
is_win_10 = is_win and (platform.win32_ver()[0] == '10')
is_cygwin = sys.platform == 'cygwin'
is_darwin = sys.platform == 'darwin'  # Mac OS X

# Unix platforms
is_linux = sys.platform.startswith('linux')
is_solar = sys.platform.startswith('sun')  # Solaris
is_aix = sys.platform.startswith('aix')
is_freebsd = sys.platform.startswith('freebsd')
is_openbsd = sys.platform.startswith('openbsd')
is_hpux = sys.platform.startswith('hp-ux')

# Some code parts are similar to several unix platforms
# (e.g. Linux, Solaris, AIX)
# Mac OS X is not considered as unix since there are many
# platform specific details for Mac in PyInstaller.
is_unix = is_linux or is_solar or is_aix or is_freebsd or is_hpux or is_openbsd


# On different platforms is different file for dynamic python library.
_pyver = sys.version_info[:2]
if is_win or is_cygwin:
    PYDYLIB_NAMES = {'python%d%d.dll' % _pyver,
                     'libpython%d%d.dll' % _pyver,
                     'libpython%d%dm.dll' % _pyver,
                     'libpython%d.%d.dll' % _pyver,
                     'libpython%d.%dm.dll' % _pyver}  # For MSYS2 environment
elif is_darwin:
    # libpython%d.%dm.dylib for Conda virtual environment installations
    PYDYLIB_NAMES = {'Python', '.Python',
                     'libpython%d.%d.dylib' % _pyver,
                     'libpython%d.%dm.dylib' % _pyver}
elif is_aix:
    # Shared libs on AIX are archives with shared object members, thus the ".a" suffix.
    # However, python 2.7.11 built with XLC produces libpython?.?.so file, too.
    PYDYLIB_NAMES = {'libpython%d.%d.a' % _pyver,
                     'libpython%d.%d.so' % _pyver}
elif is_freebsd:
    PYDYLIB_NAMES = {'libpython%d.%d.so.1' % _pyver,
                     'libpython%d.%dm.so.1' % _pyver,
                     'libpython%d.%d.so.1.0' % _pyver,
                     'libpython%d.%dm.so.1.0' % _pyver}
elif is_openbsd:
    PYDYLIB_NAMES = {'libpython%d.%d.so.0.0' % _pyver,
                     'libpython%d.%dm.so.0.0' % _pyver}
elif is_hpux:
    PYDYLIB_NAMES = {'libpython%d.%d.so' % _pyver}
elif is_unix:
    # Other *nix platforms.
    # Python 2 .so library on Linux is: libpython2.7.so.1.0
    # Python 3 .so library on Linux is: libpython3.2mu.so.1.0, libpython3.3m.so.1.0
    PYDYLIB_NAMES = {'libpython%d.%d.so.1.0' % _pyver,
                     'libpython%d.%dm.so.1.0' % _pyver,
                     'libpython%d.%dmu.so.1.0' % _pyver,
                     'libpython%d.%dm.so' % _pyver}
else:
    raise SystemExit('Your platform is not yet supported. '
                     'Please define constant PYDYLIB_NAMES for your platform.')


# Function with which to open files.
open_file = open
text_read_mode = 'r'

# In Python 3 built-in function raw_input() was renamed to just 'input()'.
stdin_input = input

# Safe repr that always outputs ascii
safe_repr = ascii

# String types to replace `isinstance(foo, str)`
# Use `isinstance(foo, string_types)` instead.
string_types = str

# Correct extension ending: 'c' or 'o'
if __debug__:
    PYCO = 'c'
else:
    PYCO = 'o'

# Options for python interpreter when invoked in a subprocess.
if __debug__:
    # Python started *without* -O
    _PYOPTS = ''
else:
    _PYOPTS = '-O'


# In a virtual environment created by virtualenv (github.com/pypa/virtualenv)
# there exists sys.real_prefix with the path to the base Python
# installation from which the virtual environment was created.
# This is true regardless of
# the version of Python used to execute the virtualenv command.
#
# In a virtual environment created by the venv module available in
# the Python standard lib, there exists sys.base_prefix with the path to
# the base implementation. This does not exist in
# a virtual environment created by virtualenv.
#
# The following code creates compat.is_venv and is.virtualenv
# that are True when running a virtual environment, and also
# compat.base_prefix with the path to the
# base Python installation.

base_prefix = getattr( sys, 'real_prefix',
                       getattr( sys, 'base_prefix', sys.prefix )
                        )
# Ensure `base_prefix` is not containing any relative parts.
base_prefix = os.path.abspath(base_prefix)
is_venv = is_virtualenv = base_prefix != os.path.abspath(sys.prefix)

# Conda environments sometimes have different paths or apply patches to
# packages that can affect how a hook or package should access resources.
# Method for determining conda taken from:
# https://stackoverflow.com/questions/47610844#47610844
is_conda = os.path.isdir(os.path.join(base_prefix, 'conda-meta'))

# In Python 3.4 module 'imp' is deprecated and there is another way how
# to obtain magic value.
import importlib.util
BYTECODE_MAGIC = importlib.util.MAGIC_NUMBER


# List of suffixes for Python C extension modules.
from importlib.machinery import EXTENSION_SUFFIXES, all_suffixes
ALL_SUFFIXES = all_suffixes()


# In Python 3 'Tkinter' has been made lowercase - 'tkinter'.
modname_tkinter = 'tkinter'


# On Windows we require pywin32-ctypes
# -> all pyinstaller modules should use win32api from PyInstaller.compat to
#    ensure that it can work on MSYS2 (which requires pywin32-ctypes)
if is_win:
    try:
        from win32ctypes.pywin32 import pywintypes  # noqa: F401
        from win32ctypes.pywin32 import win32api
    except ImportError:
        # This environment variable is set by seutp.py
        # - It's not an error for pywin32 to not be installed at that point
        if not os.environ.get('PYINSTALLER_NO_PYWIN32_FAILURE'):
            raise SystemExit('PyInstaller cannot check for assembly dependencies.\n'
                             'Please install pywin32-ctypes.\n\n'
                             'pip install pywin32-ctypes\n')


def _architecture():
    """
    Returns the bit depth of the python interpreter's architecture as
    a string ('32bit' or '64bit'). Similar to platform.architecture(),
    but with fixes for universal binaries on MacOS.
    """
    if is_darwin:
        # Darwin's platform.architecture() is buggy and always
        # returns "64bit" even for the 32bit version of Python's
        # universal binary. So we roll out our own (that works
        # on Darwin).
        if sys.maxsize > 2 ** 32:
            return '64bit'
        else:
            return '32bit'
    else:
        return platform.architecture()[0]

architecture = _architecture()
del _architecture

system = platform.system()


def _machine():
    """
    Return machine suffix to use in directory name when looking
    for bootloader.

    PyInstaller is reported to work even on ARM architecture. For that
    case `system` and `architecture` are not enough.
    Path to bootloader has to be composed from `system`, `architecture`
    and `machine` like:
        'Linux-32bit-arm'
    """
    mach = platform.machine()
    if mach.startswith('arm'):
        return 'arm'
    elif mach.startswith('aarch'):
        return 'aarch'
    else:
        # Assume x86/x86_64 machine.
        return None

machine = _machine()
del _machine


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
    Run the command specified by the passed positional arguments, optionally
    configured by the passed keyword arguments.

    .. DANGER::
       **Ignore this function's return value** -- unless this command's standard
       output contains _only_ pathnames, in which case this function returns the
       correct filesystem-encoded string expected by PyInstaller. In all other
       cases, this function's return value is _not_ safely usable. Consider
       calling the general-purpose `exec_command_stdout()` function instead.

       For backward compatibility, this function's return value non-portably
       depends on the current Python version and passed keyword arguments:

       * Under Python 2.7, this value is an **encoded `str` string** rather than
         a decoded `unicode` string. This value _cannot_ be safely used for any
         purpose (e.g., string manipulation or parsing), except to be passed
         directly to another non-Python command.
       * Under Python 3.x, this value is a **decoded `str` string**. However,
         even this value is _not_ necessarily safely usable:
         * If the `encoding` parameter is passed, this value is guaranteed to be
           safely usable.
         * Else, this value _cannot_ be safely used for any purpose (e.g.,
           string manipulation or parsing), except to be passed directly to
           another non-Python command. Why? Because this value has been decoded
           with the encoding specified by `sys.getfilesystemencoding()`, the
           encoding used by `os.fsencode()` and `os.fsdecode()` to convert from
           platform-agnostic to platform-specific pathnames. This is _not_
           necessarily the encoding with which this command's standard output
           was encoded. Cue edge-case decoding exceptions.

    Parameters
    ----------
    cmdargs : list
        Variadic list whose:
        1. Mandatory first element is the absolute path, relative path,
           or basename in the current `${PATH}` of the command to run.
        1. Optional remaining elements are arguments to pass to this command.
    encoding : str, optional
        Optional keyword argument specifying the encoding with which to decode
        this command's standard output under Python 3. As this function's return
        value should be ignored, this argument should _never_ be passed.
    __raise_ENOENT__ : boolean, optional
        Optional keyword argument to simply raise the exception if the
        executing the command fails since to the command is not found. This is
        useful to checking id a command exists.

    All remaining keyword arguments are passed as is to the `subprocess.Popen()`
    constructor.

    Returns
    ----------
    str
        Ignore this value. See discussion above.
    """

    encoding = kwargs.pop('encoding', None)
    raise_ENOENT = kwargs.pop('__raise_ENOENT__', None)
    try:
        out = subprocess.Popen(
            cmdargs, stdout=subprocess.PIPE, **kwargs).communicate()[0]
    except OSError as e:
        if raise_ENOENT and e.errno == errno.ENOENT:
            raise
        print('--' * 20, file=sys.stderr)
        print("Error running '%s':" % " ".join(cmdargs), file=sys.stderr)
        print(e, file=sys.stderr)
        print('--' * 20, file=sys.stderr)
        raise ExecCommandFailed("Error: Executing command failed!")

    # stdout/stderr are returned as a byte array NOT as string.
    # Thus we need to convert that to proper encoding.
    try:
        if encoding:
            out = out.decode(encoding)
        else:
            # If no encoding is given, assume we're reading filenames from
            # stdout only because it's the common case.
            out = os.fsdecode(out)
    except UnicodeDecodeError as e:
        # The sub-process used a different encoding,
        # provide more information to ease debugging.
        print('--' * 20, file=sys.stderr)
        print(str(e), file=sys.stderr)
        print('These are the bytes around the offending byte:',
              file=sys.stderr)
        print('--' * 20, file=sys.stderr)
        raise
    return out


def exec_command_rc(*cmdargs, **kwargs):
    """
    Return the exit code of the command specified by the passed positional
    arguments, optionally configured by the passed keyword arguments.

    Parameters
    ----------
    cmdargs : list
        Variadic list whose:
        1. Mandatory first element is the absolute path, relative path,
           or basename in the current `${PATH}` of the command to run.
        1. Optional remaining elements are arguments to pass to this command.

    All keyword arguments are passed as is to the `subprocess.call()` function.

    Returns
    ----------
    int
        This command's exit code as an unsigned byte in the range `[0, 255]`,
        where 0 signifies success and all other values failure.
    """

    # 'encoding' keyword is not supported for 'subprocess.call'.
    # Remove it thus from kwargs.
    if 'encoding' in kwargs:
        kwargs.pop('encoding')
    return subprocess.call(cmdargs, **kwargs)


def exec_command_stdout(*command_args, **kwargs):
    """
    Capture and return the standard output of the command specified by the
    passed positional arguments, optionally configured by the passed keyword
    arguments.

    Unlike the legacy `exec_command()` and `exec_command_all()` functions, this
    modern function is explicitly designed for cross-platform portability. The
    return value may be safely used for any purpose, including string
    manipulation and parsing.

    .. NOTE::
       If this command's standard output contains _only_ pathnames, this
       function does _not_ return the correct filesystem-encoded string expected
       by PyInstaller. If this is the case, consider calling the
       filesystem-specific `exec_command()` function instead.

    Parameters
    ----------
    cmdargs : list
        Variadic list whose:
        1. Mandatory first element is the absolute path, relative path,
           or basename in the current `${PATH}` of the command to run.
        1. Optional remaining elements are arguments to pass to this command.
    encoding : str, optional
        Optional name of the encoding with which to decode this command's
        standard output (e.g., `utf8`), passed as a keyword argument. If
        unpassed , this output will be decoded in a portable manner specific to
        to the current platform, shell environment, and system settings with
        Python's built-in `universal_newlines` functionality.

    All remaining keyword arguments are passed as is to the
    `subprocess.check_output()` function.

    Returns
    ----------
    str
        Unicode string of this command's standard output decoded according to
        the "encoding" keyword argument.
    """

    # Value of the passed "encoding" parameter, defaulting to None.
    encoding = kwargs.pop('encoding', None)

    # If no encoding was specified, the current locale is defaulted to. Else, an
    # encoding was specified. To ensure this encoding is respected, the
    # "universal_newlines" option is disabled if also passed. Nice, eh?
    kwargs['universal_newlines'] = encoding is None

    # Standard output captured from this command as a decoded Unicode string if
    # "universal_newlines" is enabled or an encoded byte array otherwise.
    stdout = subprocess.check_output(command_args, **kwargs)

    # Return a Unicode string, decoded from this encoded byte array if needed.
    return stdout if encoding is None else stdout.decode(encoding)


def exec_command_all(*cmdargs, **kwargs):
    """
    Run the command specified by the passed positional arguments, optionally
    configured by the passed keyword arguments.

    .. DANGER::
       **Ignore this function's return value.** If this command's standard
       output consists solely of pathnames, consider calling `exec_command()`;
       else, consider calling `exec_command_stdout()`.

    Parameters
    ----------
    cmdargs : list
        Variadic list whose:
        1. Mandatory first element is the absolute path, relative path,
           or basename in the current `${PATH}` of the command to run.
        1. Optional remaining elements are arguments to pass to this command.
    encoding : str, optional
        Optional keyword argument specifying the encoding with which to decode
        this command's standard output. As this function's return
        value should be ignored, this argument should _never_ be passed.

    All remaining keyword arguments are passed as is to the `subprocess.Popen()`
    constructor.

    Returns
    ----------
    (int, str, str)
        Ignore this 3-element tuple `(exit_code, stdout, stderr)`. See the
        `exec_command()` function for discussion.
    """
    encoding = kwargs.pop('encoding', None)
    proc = subprocess.Popen(cmdargs, bufsize=-1,  # Default OS buffer size.
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
    # Waits for subprocess to complete.
    out, err = proc.communicate()
    # stdout/stderr are returned as a byte array NOT as string.
    # Thus we need to convert that to proper encoding.
    try:
        if encoding:
            out = out.decode(encoding)
            err = err.decode(encoding)
        else:
            # If no encoding is given, assume we're reading filenames from
            # stdout only because it's the common case.
            out = os.fsdecode(out)
            err = os.fsdecode(err)
    except UnicodeDecodeError as e:
        # The sub-process used a different encoding,
        # provide more information to ease debugging.
        print('--' * 20, file=sys.stderr)
        print(str(e), file=sys.stderr)
        print('These are the bytes around the offending byte:',
              file=sys.stderr)
        print('--' * 20, file=sys.stderr)
        raise

    return proc.returncode, out, err


def __wrap_python(args, kwargs):
    cmdargs = [sys.executable]

    # Mac OS X supports universal binaries (binary for multiple architectures.
    # We need to ensure that subprocess binaries are running for the same
    # architecture as python executable.
    # It is necessary to run binaries with 'arch' command.
    if is_darwin:
        mapping = {'32bit': '-i386', '64bit': '-x86_64'}
        py_prefix = ['arch', mapping[architecture]]
        # Since OS X 10.11 the environment variable DYLD_LIBRARY_PATH is no
        # more inherited by child processes, so we proactively propagate
        # the current value using the `-e` option of the `arch` command.
        if 'DYLD_LIBRARY_PATH' in os.environ:
            path = os.environ['DYLD_LIBRARY_PATH']
            py_prefix += ['-e', 'DYLD_LIBRARY_PATH=%s' % path]
        cmdargs = py_prefix + cmdargs

    if _PYOPTS:
        cmdargs.append(_PYOPTS)

    cmdargs.extend(args)

    env = kwargs.get('env')
    if env is None:
        env = dict(**os.environ)

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


## Path handling.

def expand_path(path):
    """
    Replace initial tilde '~' in path with user's home directory and also
    expand environment variables (${VARNAME} - Unix, %VARNAME% - Windows).
    """
    return os.path.expandvars(os.path.expanduser(path))

# Site-packages functions - use native function if available.
if hasattr(site, 'getsitepackages'):
    getsitepackages = site.getsitepackages
# Backported for virtualenv.
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

# Wrapper to load a module from a Python source file.
# This function loads import hooks when processing them.
import importlib.machinery
def importlib_load_source(name, pathname):
    # Import module from a file.
    mod_loader = importlib.machinery.SourceFileLoader(name, pathname)
    return mod_loader.load_module()


# Patterns of module names that should be bundled into the base_library.zip.

PY3_BASE_MODULES = {
    # Python 3.x
    # These modules are direct or indirect dependencies of encodings.* modules.
    # encodings modules must be recursively included to set the I/O encoding during
    # python startup.
    '_bootlocale',
    '_collections_abc',
    '_weakrefset',
    'abc',
    'codecs',
    'collections',
    'copyreg',
    'encodings',
    'enum',
    'functools',
    'io',
    'heapq',
    'keyword',
    'linecache',
    'locale',
    'operator',
    're',
    'reprlib',
    'sre_compile',
    'sre_constants',
    'sre_parse',
    'traceback',  # for startup errors
    'types',
    'weakref',
    'warnings',
}

# Object types of Pure Python modules in modulegraph dependency graph.
# Pure Python modules have code object (attribute co_code).
PURE_PYTHON_MODULE_TYPES = {
    'SourceModule',
    'CompiledModule',
    'Package',
    'NamespacePackage',
    # Deprecated.
    # TODO Could these module types be removed?
    'FlatPackage',
    'ArchiveModule',
}
# Object types of special Python modules (built-in, run-time, namespace package)
# in modulegraph dependency graph that do not have code object.
SPECIAL_MODULE_TYPES = {
    'AliasNode',
    'BuiltinModule',
    'RuntimeModule',
    'RuntimePackage',

    # PyInstaller handles scripts differently and not as standard Python modules.
    'Script',
}
# Object types of Binary Python modules (extensions, etc) in modulegraph
# dependency graph.
BINARY_MODULE_TYPES = {
    'Extension',
}
# Object types of valid Python modules in modulegraph dependency graph.
VALID_MODULE_TYPES = PURE_PYTHON_MODULE_TYPES | SPECIAL_MODULE_TYPES | BINARY_MODULE_TYPES
# Object types of bad/missing/invalid Python modules in modulegraph
# dependency graph.
# TODO Should be 'Invalid' module types also in the 'MISSING' set?
BAD_MODULE_TYPES = {
    'BadModule',
    'ExcludedModule',
    'InvalidSourceModule',
    'InvalidCompiledModule',
    'MissingModule',

    # Runtime modules and packages are technically valid rather than bad, but
    # exist only in-memory rather than on-disk (typically due to
    # pre_safe_import_module() hooks) and hence cannot be physically frozen.
    # For simplicity, these nodes are categorized as bad rather than valid.
    'RuntimeModule',
    'RuntimePackage',
}
ALL_MODULE_TYPES = VALID_MODULE_TYPES | BAD_MODULE_TYPES
# TODO Review this mapping to TOC, remove useless entries.
# Dict to map ModuleGraph node types to TOC typecodes
MODULE_TYPES_TO_TOC_DICT = {
    # Pure modules.
    'AliasNode': 'PYMODULE',
    'Script': 'PYSOURCE',
    'SourceModule': 'PYMODULE',
    'CompiledModule': 'PYMODULE',
    'Package': 'PYMODULE',
    'FlatPackage': 'PYMODULE',
    'ArchiveModule': 'PYMODULE',
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
    'RuntimeModule': 'runtime',
    'RuntimePackage': 'runtime',
    # Other.
    'does not occur': 'BINARY',
}


def check_requirements():
    """
    Verify that all requirements to run PyInstaller are met.

    Fail hard if any requirement is not met.
    """
    # Fail hard if Python does not have minimum required version
    if not is_py35:
        raise SystemExit('PyInstaller requires at least Python 3.5 or newer. '
                         'The last version supporting Python 2.7 was v3.6.')
