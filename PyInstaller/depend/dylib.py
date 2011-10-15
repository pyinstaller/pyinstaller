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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA

# Note also that you should check the results to make sure that the
# dlls are redistributable. I've listed most of the common MS dlls
# under "excludes" below; add to this list as necessary (or use the
# "excludes" option in the INSTALL section of the config file).

"""
Manipulating with dynamic libraries.
"""


__all__ = ['exclude_list', 'include_list', 'include_library']

import os
import re

from PyInstaller import is_win, is_unix, is_darwin


import PyInstaller.log as logging
logger = logging.getLogger('PyInstaller.build.bindepend')


# Regex excludes
_excludes = {}
# Regex includes - overrides excludes.
_includes = {}


_win_excludes = {
    # MS assembly excludes
    r'^Microsoft\.Windows\.Common-Controls$': 1,
}


_unix_excludes = {
    r'/libc\.so\..*': 1,
    r'/libdl\.so\..*': 1,
    r'/libm\.so\..*': 1,
    r'/libpthread\.so\..*': 1,
    r'/librt\.so\..*': 1,
    r'/libthread_db\.so\..*': 1,
    r'/libdb-.*\.so': 1,
    # glibc regex excludes.
    r'/ld-linux\.so\..*': 1,
    r'/libBrokenLocale\.so\..*': 1,
    r'/libanl\.so\..*': 1,
    r'/libcidn\.so\..*': 1,
    r'/libcrypt\.so\..*': 1,
    r'/libnsl\.so\..*': 1,
    r'/libnss_compat.*\.so\..*': 1,
    r'/libnss_dns.*\.so\..*': 1,
    r'/libnss_files.*\.so\..*': 1,
    r'/libnss_hesiod.*\.so\..*': 1,
    r'/libnss_nis.*\.so\..*': 1,
    r'/libnss_nisplus.*\.so\..*': 1,
    r'/libresolv\.so\..*': 1,
    r'/libutil\.so\..*': 1,
    # libGL can reference some hw specific libraries (like nvidia libs).
    r'/libGL\..*': 1,
}


if is_win:
    _excludes = _win_excludes
    from PyInstaller.utils import winutils
    sep = '[%s]' % re.escape(os.sep + os.altsep)
    # Exclude everything from the Windows directory by default.
    _excludes['^%s%s' % (re.escape(winutils.get_windows_dir()), sep)] = 1
    # Allow pythonNN.dll, pythoncomNN.dll, pywintypesNN.dll
    _includes[r'%spy(?:thon(?:com(?:loader)?)?|wintypes)\d+\.dll$' % sep] = 1


elif is_unix:
    _excludes = _unix_excludes


class ExcludeList(object):
    def __init__(self):
        self.regex = re.compile('|'.join(_excludes.keys()), re.I)

    def search(self, libname):
        # Running re.search() on '' regex never returns None.
        if _excludes:
            return self.regex.search(libname)
        else:
            return False


class IncludeList(object):
    def __init__(self):
        self.regex = re.compile('|'.join(_includes.keys()), re.I)

    def search(self, libname):
        # Running re.search() on '' regex never returns None.
        if _includes:
            return self.regex.search(libname)
        else:
            return False


exclude_list = ExcludeList()
include_list = IncludeList()


if is_darwin:
    # On Mac use macholib to decide if a binary is a system one.
    from PyInstaller.lib.macholib import util

    class MacExcludeList(object):
        def search(self, libname):
            return util.in_system_path(libname)

    exclude_list = MacExcludeList()


def include_library(libname):
    """Check if a dynamic library should be included with application or not."""
    # For configuration phase we need to have exclude / include lists None
    # so these checking is skipped.
    if exclude_list and include_list:
        return (exclude_list.search(libname) and
            not include_list.search(libname))
