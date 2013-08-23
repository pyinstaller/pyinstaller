#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Various classes and functions to provide some backwards-compatibility
with previous versions of Python from 2.3 onward.
"""


import dircache  # Module removed in Python 3
import os
import platform
import subprocess
import sys


is_py25 = sys.version_info >= (2, 5)
is_py26 = sys.version_info >= (2, 6)
is_py27 = sys.version_info >= (2, 7)

is_win = sys.platform.startswith('win')
is_cygwin = sys.platform == 'cygwin'
is_darwin = sys.platform == 'darwin'  # Mac OS X

# Unix platforms
is_linux = sys.platform.startswith('linux')
is_solar = sys.platform.startswith('sun')  # Solaris
is_aix = sys.platform.startswith('aix')

# Some code parts are similar to several unix platforms
# (e.g. Linux, Solaris, AIX)
# Mac OS X is not considered as unix since there are many
# platform specific details for Mac in PyInstaller.
is_unix = is_linux or is_solar or is_aix


# Correct extension ending: 'c' or 'o'
if __debug__:
    PYCO = 'c'
else:
    PYCO = 'o'


# If ctypes is present, specific dependency discovery can be enabled.
try:
    import ctypes
except ImportError:
    ctypes = None


if 'PYTHONCASEOK' not in os.environ:
    def caseOk(filename):
        files = dircache.listdir(os.path.dirname(filename))
        return os.path.basename(filename) in files
else:
    def caseOk(filename):
        return True


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
_PYOPTS = __debug__ and '-O' or ''


try:
    # Python 2.5+
    import hashlib
except ImportError:
    class hashlib(object):
        from md5 import new as md5
        from sha import new as sha


# Function os.path.relpath() available in Python 2.6+.
if hasattr(os.path, 'relpath'):
    from os.path import relpath
# Own implementation of relpath function.
else:
    def relpath(path, start=os.curdir):
        """
        Return a relative version of a path.
        """
        if not path:
            raise ValueError("no path specified")
        # Normalize paths.
        path = os.path.normpath(path)
        start = os.path.abspath(start) + os.sep  # os.sep has to be here.
        # Get substring.
        relative = path[len(start):len(path)]
        return relative


# Some code parts needs to behave different when running in virtualenv.
# 'real_prefix is for virtualenv,
# 'base_prefix' is for PEP 405 venv (new in Python 3.3)
venv_real_prefix = (getattr(sys, 'real_prefix', None) or
                    getattr(sys, 'base_prefix', None))
is_virtualenv = bool(venv_real_prefix)


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
        if sys.maxint > 2L ** 32:
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


def exec_command(*cmdargs):
    """
    Wrap creating subprocesses

    Return stdout of the invoked command.
    Todo: Use module `subprocess` if available, else `os.system()`
    """
    return subprocess.Popen(cmdargs, stdout=subprocess.PIPE).communicate()[0]


def exec_command_rc(*cmdargs, **kwargs):
    """
    Wrap creating subprocesses.

    Return exit code of the invoked command.
    Todo: Use module `subprocess` if available, else `os.system()`
    """
    return subprocess.call(cmdargs, **kwargs)


def exec_command_all(*cmdargs, **kwargs):
    """
    Wrap creating subprocesses

    Return tuple (exit_code, stdout, stderr) of the invoked command.
    """
    proc = subprocess.Popen(cmdargs, bufsize=-1,  # Default OS buffer size.
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
    # Waits for subprocess to complete.
    out, err = proc.communicate()

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


# The function os.getcwd() does not work with unicode paths on Windows.
def getcwd():
    """
    Wrap os.getcwd()

    On Windows return ShortPathName (8.3 filename) that contain only ascii
    characters.
    """
    cwd = os.getcwd()
    # TODO os.getcwd should work properly with py3 on windows.
    if is_win:
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
