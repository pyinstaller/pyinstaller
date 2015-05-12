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
is_py33 = sys.version_info >= (3, 3) and sys.version_info < (3, 4)
is_py34 = sys.version_info >= (3, 4) and sys.version_info < (3, 5)

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


# In Python 3 built-in function raw_input() was renamed to just 'input()'.
try:
    stdin_input = raw_input
except NameError:
    stdin_input = input



# UserList class is moved to 'collections.UserList in Python 3.
if is_py2:
    from UserList import UserList
else:
    from collections import UserList


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
if is_py2:
    import imp
    BYTECODE_MAGIC = imp.get_magic()
else:
    if is_py34:
        import importlib.util
        BYTECODE_MAGIC = importlib.util.MAGIC_NUMBER
    else:
        import importlib._bootstrap
        # TODO verify this works with Python 3.2
        BYTECODE_MAGIC = importlib._bootstrap._MAGIC_BYTES


# List of suffixes for Python C extension modules.
if is_py2:
    # TODO implement getting extension suffixes for Python 2 or older Python 3.
    EXTENSION_SUFFIXES = ['.so']
else:
    # In Python 3.3+ There is a list
    import importlib.machinery
    EXTENSION_SUFFIXES = importlib.machinery.EXTENSION_SUFFIXES


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


def exec_command(*cmdargs):
    """
    Wrap creating subprocesses

    Return stdout of the invoked command.
    """
    out = subprocess.Popen(cmdargs, stdout=subprocess.PIPE).communicate()[0]
    # Python 3 returns stdout/stderr as a byte array NOT as string.
    # Thus we need to convert that to proper encoding.
    # Let' suppose that stdout/stderr will contain only utf-8 or ascii
    # characters.
    return out.decode('utf-8')


def exec_command_rc(*cmdargs, **kwargs):
    """
    Wrap creating subprocesses.

    Return exit code of the invoked command.
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
    # Python 3 returns stdout/stderr as a byte array NOT as string.
    # Thus we need to convert that to proper encoding.
    # Let' suppose that stdout/stderr will contain only utf-8 or ascii
    # characters.
    return proc.returncode, out.decode('utf-8'), err.decode('utf-8')


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
