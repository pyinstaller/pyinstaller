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

"""
Utils for Windows platform.
"""


__all__ = ['get_windows_dir']

import os

from PyInstaller import is_win
from PyInstaller import compat

import PyInstaller.log as logging
logger = logging.getLogger('PyInstaller.build.bindepend')


def get_windows_dir():
    """Return the Windows directory e.g. C:\\Windows"""
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
    """Return the path that Windows will search for dlls."""
    _bpath = []
    if is_win:
        try:
            import win32api
        except ImportError:
            logger.warn("Cannot determine your Windows or System directories")
            logger.warn("Please add them to your PATH if .dlls are not found")
            logger.warn("or install http://sourceforge.net/projects/pywin32/")
        else:
            sysdir = win32api.GetSystemDirectory()
            sysdir2 = os.path.normpath(os.path.join(sysdir, '..', 'SYSTEM'))
            windir = win32api.GetWindowsDirectory()
            _bpath = [sysdir, sysdir2, windir]
    _bpath.extend(compat.getenv('PATH', '').split(os.pathsep))
    return _bpath
