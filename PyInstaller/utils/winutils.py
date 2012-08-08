#
# Copyright (C) 2005-2011, Giovanni Bajo
# Based on previous work under copyright (c) 2002 McMillan Enterprises, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA


# Utils for Windows platform.


__all__ = ['get_windows_dir']

import os

from PyInstaller import compat

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
