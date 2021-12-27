#-----------------------------------------------------------------------------
# Copyright (c) 2013-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""
Utilities for Windows platform.
"""

import os
import sys

import PyInstaller.log as logging
from PyInstaller import compat

logger = logging.getLogger(__name__)


def get_windows_dir():
    """
    Return the Windows directory, e.g., C:\\Windows.
    """
    # Imported here to avoid circular import.
    from PyInstaller import compat
    windir = compat.win32api.GetWindowsDirectory()
    if not windir:
        raise SystemExit("Error: Cannot determine Windows directory!")
    return windir


def get_system_path():
    """
    Return the required Windows system paths.
    """
    # Imported here to avoid circular import.
    from PyInstaller import compat
    _bpath = []
    sys_dir = compat.win32api.GetSystemDirectory()
    # Ensure C:\Windows\system32  and C:\Windows directories are always present in PATH variable.
    # C:\Windows\system32 is valid even for 64-bit Windows. Access do DLLs are transparently redirected to
    # C:\Windows\syswow64 for 64bit applactions.
    # See http://msdn.microsoft.com/en-us/library/aa384187(v=vs.85).aspx
    _bpath = [sys_dir, get_windows_dir()]
    return _bpath


def extend_system_path(paths):
    """
    Add new paths at the beginning of environment variable PATH.

    Some hooks might extend PATH where PyInstaller should look for dlls.
    """
    # imported here to avoid circular import
    from PyInstaller import compat
    old_path = compat.getenv('PATH', '')
    paths.append(old_path)
    new_path = os.pathsep.join(paths)
    compat.setenv('PATH', new_path)


def import_pywin32_module(module_name):
    """
    Import and return the PyWin32 module with the passed name.

    When imported, the `pywintypes` and `pythoncom` modules both internally import dynamic libraries
    (e.g., `pywintypes.py` imports `pywintypes34.dll` under Python 3.4). The Anaconda Python distribution for Windows
    installs these libraries to non-standard directories, resulting in
    `"ImportError: No system module 'pywintypes' (pywintypes34.dll)"`
    exceptions. This function catches these exceptions, searches for these libraries, adds their directories to
    `sys.path`, and retries.

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
        module = __import__(module_name, globals={}, locals={}, fromlist=[''])
    except ImportError as exc:
        if str(exc).startswith('No system module'):
            # True if "sys.frozen" is currently set.
            is_sys_frozen = hasattr(sys, 'frozen')

            # Current value of "sys.frozen" if any.
            sys_frozen = getattr(sys, 'frozen', None)

            # Force PyWin32 to search "sys.path" for DLLs. By default, PyWin32 only searches "site-packages\win32\lib",
            # "sys.prefix", and Windows system directories (e.g., "C:\Windows\System32"). This is an ugly hack, but
            # there is no other way.
            sys.frozen = '|_|GLYH@CK'

            # If isolated to a venv, the preferred site.getsitepackages() function is unreliable. Fall back to searching
            # "sys.path" instead.
            if compat.is_venv:
                sys_paths = sys.path
            else:
                sys_paths = compat.getsitepackages()

            for sys_path in sys_paths:
                # Absolute path of the directory containing PyWin32 DLLs.
                pywin32_dll_dir = os.path.join(sys_path, 'pywin32_system32')
                if os.path.isdir(pywin32_dll_dir):
                    sys.path.append(pywin32_dll_dir)
                    try:
                        module = __import__(name=module_name, globals={}, locals={}, fromlist=[''])
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
    # Imported here to avoid circular import.
    if isinstance(dll_name, bytes):
        return str(dll_name, encoding='UTF-8')
    else:
        return dll_name


def fixup_exe_headers(exe_path, timestamp=None):
    """
    Set executable's checksum and build timestamp in its headers.

    This optional checksum is supposed to protect the executable against corruption but some anti-viral software have
    taken to flagging anything without it set correctly as malware. See issue #5579.
    """
    import pefile
    pe = pefile.PE(exe_path, fast_load=False)  # full load because we need all headers
    # Set build timestamp.
    # See: https://0xc0decafe.com/malware-analyst-guide-to-pe-timestamps
    if timestamp is not None:
        timestamp = int(timestamp)
        # Set timestamp field in FILE_HEADER
        pe.FILE_HEADER.TimeDateStamp = timestamp
        # MSVC-compiled executables contain (at least?) one DIRECTORY_ENTRY_DEBUG entry that also contains timestamp
        # with same value as set in FILE_HEADER. So modify that as well, as long as it is set.
        debug_entries = getattr(pe, 'DIRECTORY_ENTRY_DEBUG', [])
        for debug_entry in debug_entries:
            if debug_entry.struct.TimeDateStamp:
                debug_entry.struct.TimeDateStamp = timestamp
    # Set PE checksum
    pe.OPTIONAL_HEADER.CheckSum = pe.generate_checksum()
    pe.close()
    pe.write(exe_path)
