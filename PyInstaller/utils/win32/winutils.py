#-----------------------------------------------------------------------------
# Copyright (c) 2013-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Utils for Windows platform.
"""

__all__ = ['get_windows_dir']

import os
import sys

from PyInstaller import compat
from PyInstaller.compat import is_py3

import PyInstaller.log as logging
logger = logging.getLogger(__name__)


def get_windows_dir():
    """
    Return the Windows directory e.g. C:\\Windows.
    """
    try:
        import win32api
    except ImportError:
        windir = compat.getenv('SystemRoot', compat.getenv('WINDIR'))
    else:
        windir = win32api.GetWindowsDirectory()
    if not windir:
        raise SystemExit("Error: Can not determine your Windows directory")
    return windir


def get_system_path():
    """
    Return the path that Windows will search for dlls.
    """
    _bpath = []
    try:
        import win32api
        sys_dir = win32api.GetSystemDirectory()
    except ImportError:
        sys_dir = os.path.normpath(os.path.join(get_windows_dir(), 'system32'))
    # Ensure C:\Windows\system32  and C:\Windows directories are
    # always present in PATH variable.
    # C:\Windows\system32 is valid even for 64bit Windows. Access do DLLs are
    # transparently redirected to C:\Windows\syswow64 for 64bit applactions.
    # http://msdn.microsoft.com/en-us/library/aa384187(v=vs.85).aspx
    _bpath = [sys_dir, get_windows_dir()]
    _bpath.extend(compat.getenv('PATH', '').split(os.pathsep))
    return _bpath


def extend_system_path(paths):
    """
    Add new paths at the beginning of environment variable PATH.

    Some hooks might extend PATH where PyInstaller should look for dlls.
    """
    old_PATH = compat.getenv('PATH', '')
    paths.append(old_PATH)
    new_PATH = os.pathsep.join(paths)
    compat.setenv('PATH', new_PATH)


def import_pywin32_module(module_name):
    """
    Import and return the PyWin32 module with the passed name.

    When imported, the `pywintypes` and `pythoncom` modules both internally
    import dynamic libraries (e.g., `pywintypes.py` imports `pywintypes34.dll`
    under Python 3.4). The Anaconda Python distribution for Windows installs
    these libraries to non-standard directories, resulting in
    `"ImportError: No system module 'pywintypes' (pywintypes34.dll)"`
    exceptions. This function catches these exceptions, searches for these
    libraries, adds their directories to `sys.path`, and retries.

    Parameters
    ----------
    module_name : str
        Fully-qualified name of this module.

    Returns
    ----------
    types.ModuleType
        The desired module.
    """
    module = None

    try:
        module = __import__(
            name=module_name, globals={}, locals={}, fromlist=[''])
    except ImportError as exc:
        if str(exc).startswith('No system module'):
            # True if "sys.frozen" is currently set.
            is_sys_frozen = hasattr(sys, 'frozen')

            # Current value of "sys.frozen" if any.
            sys_frozen = getattr(sys, 'frozen', None)

            # Force PyWin32 to search "sys.path" for DLLs. By default, PyWin32
            # only searches "site-packages\win32\lib/", "sys.prefix", and
            # Windows system directories (e.g., "C:\Windows\System32"). This is
            # an ugly hack, but there is no other way.
            sys.frozen = '|_|GLYH@CK'

            # If isolated to a venv, the preferred site.getsitepackages()
            # function is unreliable. Fallback to searching "sys.path" instead.
            if compat.is_venv:
                sys_paths = sys.path
            else:
                import site
                sys_paths = site.getsitepackages()

            for sys_path in sys_paths:
                # Absolute path of the directory containing PyWin32 DLLs.
                pywin32_dll_dir = os.path.join(sys_path, 'pywin32_system32')
                if os.path.isdir(pywin32_dll_dir):
                    sys.path.append(pywin32_dll_dir)
                    try:
                        module = __import__(
                            name=module_name, globals={}, locals={}, fromlist=[''])
                        break
                    except ImportError:
                        pass

            # If "sys.frozen" was previously set, restore its prior value.
            if is_sys_frozen:
                sys.frozen = sys_frozen
            # Else, undo this hack entirely.
            else:
                del sys.frozen

        # If this module remains unimportable, PyWin32 is not installed. Fail.
        if module is None:
            raise

    return module


def convert_dll_name_to_str(dll_name):
    """
    Convert dll names from 'bytes' to 'str'.

    Latest pefile returns type 'bytes'.
    :param dll_name:
    :return:
    """
    if is_py3 and isinstance(dll_name, bytes):
        return str(dll_name, encoding='UTF-8')
    else:
        return dll_name