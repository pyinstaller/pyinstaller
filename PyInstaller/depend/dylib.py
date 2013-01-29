#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Manipulating with dynamic libraries.
"""


__all__ = ['exclude_list', 'include_list', 'include_library']


import os
import re


from PyInstaller.compat import is_win, is_unix, is_aix, is_darwin


import PyInstaller.log as logging
logger = logging.getLogger(__name__)


_BOOTLOADER_FNAMES = set(['run', 'run_d', 'runw', 'runw_d'])


# Regex excludes
# Ignoring some system libraries speeds up packaging process
_excludes = {}
# Regex includes - overrides excludes.
# Include list is used only to override specific libraries
# from exclude list.
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

_aix_excludes = {
    r'/libbz2\.a': 1,
    r'/libc\.a': 1,
    r'/libC\.a': 1,
    r'/libcrypt\.a': 1,
    r'/libdl\.a': 1,
    r'/libintl\.a': 1,
    r'/libpthreads\.a': 1,
    r'/librt\\.a': 1,
    r'/librtl\.a': 1,
    r'/libz\.a': 1,
}


if is_win:
    _excludes = _win_excludes
    from PyInstaller.utils import winutils
    sep = '[%s]' % re.escape(os.sep + os.altsep)
    # Exclude everything from the Windows directory by default.
    windir = re.escape(winutils.get_windows_dir())
    _excludes['^%s%s' % (windir, sep)] = 1
    # Allow pythonNN.dll, pythoncomNN.dll, pywintypesNN.dll
    _includes[r'%spy(?:thon(?:com(?:loader)?)?|wintypes)\d+\.dll$' % sep] = 1

elif is_aix:
    # The exclude list for AIX differs from other *nix platforms.
    _excludes = _aix_excludes
elif is_unix:
    # Common excludes for *nix platforms -- except AIX.
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
    """
    Check if a dynamic library should be included with application or not.
    """
    # For configuration phase we need to have exclude / include lists None
    # so these checking is skipped and library gets included.
    if exclude_list:
        if exclude_list.search(libname) and not include_list.search(libname):
            # Library is excluded and is not overriden by include list.
            # It should be then excluded.
            return False
        else:
            # Include library
            return True
    else:
        # By default include library.
        return True


def mac_set_relative_dylib_deps(libname, distname):
    """
    On Mac OS X set relative paths to dynamic library dependencies
    of `libname`.

    Relative paths allow to avoid using environment variable DYLD_LIBRARY_PATH.
    There are known some issues with DYLD_LIBRARY_PATH. Relative paths is
    more flexible mechanism.

    Current location of dependend libraries is derived from the location
    of the library path (paths start with '@loader_path').

    'distname'  path of the library relative to dist directory of frozen
                executable. We need this to determine the level of directory
                level for @loader_path of binaries not found in dist directory.

                E.g. qt4 plugins are not in the same directory as Qt*.dylib
                files. Without using '@loader_path/../..' for qt plugins
                Mac OS X would not be able to resolve shared library
                dependencies and qt plugins will not be loaded.
    """

    from PyInstaller.lib.macholib import util
    from PyInstaller.lib.macholib.MachO import MachO

    # Ignore bootloader otherwise PyInstaller fails with exception like
    # 'ValueError: total_size > low_offset (288 > 0)'
    if os.path.basename(libname) in _BOOTLOADER_FNAMES:
        return

    # Determine how many directories up is the directory with shared
    # dynamic libraries. '../'
    # E.g.  ./qt4_plugins/images/ -> ./../../
    parent_dir = ''
    # Check if distname is not only base filename.
    if os.path.dirname(distname):
        parent_level = len(os.path.dirname(distname).split(os.sep))
        parent_dir = parent_level * (os.pardir + os.sep)

    def match_func(pth):
        """
        For system libraries is still used absolute path. It is unchanged.
        """
        # Match non system dynamic libraries.
        if not util.in_system_path(pth):
            # Use relative path to dependend dynamic libraries bases on
            # location of the executable.
            return os.path.join('@loader_path', parent_dir,
                os.path.basename(pth))

    # Rewrite mach headers with @loader_path.
    dll = MachO(libname)
    dll.rewriteLoadCommands(match_func)

    # Write changes into file.
    # Write code is based on macholib example.
    try:
        f = open(dll.filename, 'rb+')
        for header in dll.headers:
            f.seek(0)
            dll.write(f)
        f.seek(0, 2)
        f.flush()
        f.close()
    except Exception:
        pass
