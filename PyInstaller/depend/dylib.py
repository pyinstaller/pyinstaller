#-----------------------------------------------------------------------------
# Copyright (c) 2013-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Manipulating with dynamic libraries.
"""

import os.path

from PyInstaller.utils.win32 import winutils


__all__ = ['exclude_list', 'include_list', 'include_library']


import os
import re


from PyInstaller.compat import is_win, is_unix, is_aix, is_darwin


import PyInstaller.log as logging
logger = logging.getLogger(__name__)


_BOOTLOADER_FNAMES = set(['run', 'run_d', 'runw', 'runw_d'])


# Ignoring some system libraries speeds up packaging process
_excludes = set([
    # Ignore annoying warnings with Windows system dlls.
    #
    # 'W: library kernel32.dll required via ctypes not found'
    # 'W: library coredll.dll required via ctypes not found'
    #
    # These these dlls has to be ignored for all operating systems
    # because they might be resolved when scanning code for ctypes
    # dependencies.
    r'advapi32\.dll',
    r'ws2_32\.dll',
    r'gdi32\.dll',
    r'oleaut32\.dll',
    r'shell32\.dll',
    r'ole32\.dll',

    r'coredll\.dll',
    r'crypt32\.dll',
    r'kernel32',
    r'kernel32\.dll',
    r'msvcrt\.dll',
    r'rpcrt4\.dll',
    r'user32\.dll',
    # Some modules tries to import the Python library.
    # e.g. pyreadline.console.console
    r'python\%s\%s',
])

# Regex includes - overrides excludes.
# Include list is used only to override specific libraries
# from exclude list.
_includes = set()


_win_includes = set([
    # DLLs are from 'Microsoft Visual C++ 2010 Redistributable Package'.
    # http://msdn.microsoft.com/en-us/library/8kche8ah(v=vs.100).aspx
    #
    # Python 3.3 and 3.4 depends use Visual Studio C++ 2010 for Windows builds.
    # python33.dll depends on msvcr100.dll.
    #
    # Visual Studio C++ 2010 does not need Assembly manifests anymore and
    # uses C++ runtime libraries the old way - pointing to C:\Windows\System32.
    # It is necessary to allow inclusion of these libraries from C:\Windows\System32.
    r'atl100\.dll',
    r'msvcr100\.dll',
    r'msvcp100\.dll',
    r'mfc100\.dll',
    r'mfc100u\.dll',
    r'mfcmifc80\.dll',
    r'mfcm100\.dll',
    r'mfcm100u\.dll',

    # Python 3.5 uses the Univeral C Runtime which consists of these DLLs:
    r'api-ms-win-core.*',
    r'api-ms-win-crt.*',
    r'ucrtbase\.dll',
    r'vcruntime140\.dll',

    # Allow pythonNN.dll, pythoncomNN.dll, pywintypesNN.dll
    r'py(?:thon(?:com(?:loader)?)?|wintypes)\d+\.dll',
])

_win_excludes = set([
    # On Windows, only .dll files can be loaded.
    r'.*\.so',
    r'.*\.dylib',

    # MS assembly excludes
    r'Microsoft\.Windows\.Common-Controls',
])


_unix_excludes = set([
    r'libc\.so(\..*)?',
    r'libdl\.so(\..*)?',
    r'libm\.so(\..*)?',
    r'libpthread\.so(\..*)?',
    r'librt\.so(\..*)?',
    r'libthread_db\.so(\..*)?',
    # glibc regex excludes.
    r'ld-linux\.so(\..*)?',
    r'libBrokenLocale\.so(\..*)?',
    r'libanl\.so(\..*)?',
    r'libcidn\.so(\..*)?',
    r'libcrypt\.so(\..*)?',
    r'libnsl\.so(\..*)?',
    r'libnss_compat.*\.so(\..*)?',
    r'libnss_dns.*\.so(\..*)?',
    r'libnss_files.*\.so(\..*)?',
    r'libnss_hesiod.*\.so(\..*)?',
    r'libnss_nis.*\.so(\..*)?',
    r'libnss_nisplus.*\.so(\..*)?',
    r'libresolv\.so(\..*)?',
    r'libutil\.so(\..*)?',
    # libGL can reference some hw specific libraries (like nvidia libs).
    r'libGL\..*',
    # libxcb-dri changes ABI frequently (e.g.: between Ubuntu LTS releases) and
    # is usually installed as dependency of the graphics stack anyway. No need
    # to bundle it.
    r'libxcb\.so(\..*)?',
    r'libxcb-dri.*\.so(\..*)?',
])

_aix_excludes = set([
    r'libbz2\.a',
    r'libc\.a',
    r'libC\.a',
    r'libcrypt\.a',
    r'libdl\.a',
    r'libintl\.a',
    r'libpthreads\.a',
    r'librt\\.a',
    r'librtl\.a',
    r'libz\.a',
])


if is_win:
    _includes |= _win_includes
    _excludes |= _win_excludes
elif is_aix:
    # The exclude list for AIX differs from other *nix platforms.
    _excludes |= _aix_excludes
elif is_unix:
    # Common excludes for *nix platforms -- except AIX.
    _excludes |= _unix_excludes


class ExcludeList(object):
    def __init__(self):
        self.regex = re.compile('|'.join(_excludes), re.I)

    def search(self, libname):
        # Running re.search() on '' regex never returns None.
        if _excludes:
            return self.regex.match(os.path.basename(libname))
        else:
            return False


class IncludeList(object):
    def __init__(self):
        self.regex = re.compile('|'.join(_includes), re.I)

    def search(self, libname):
        # Running re.search() on '' regex never returns None.
        if _includes:
            return self.regex.match(os.path.basename(libname))
        else:
            return False


exclude_list = ExcludeList()
include_list = IncludeList()


if is_darwin:
    # On Mac use macholib to decide if a binary is a system one.
    from macholib import util

    class MacExcludeList(object):
        def __init__(self, global_exclude_list):
            # Wraps the global 'exclude_list' before it is overriden
            # by this class.
            self._exclude_list = global_exclude_list

        def search(self, libname):
            # First try global exclude list. If it matches then
            # return it's result otherwise continue with other check.
            result = self._exclude_list.search(libname)
            if result:
                return result
            else:
                return util.in_system_path(libname)

    exclude_list = MacExcludeList(exclude_list)

elif is_win:
    class WinExcludeList(object):
        def __init__(self, global_exclude_list):
            self._exclude_list = global_exclude_list
            # use normpath because msys2 uses / instead of \
            self._windows_dir = os.path.normpath(winutils.get_windows_dir().lower())

        def search(self, libname):
            libname = libname.lower()
            result = self._exclude_list.search(libname)
            if result:
                return result
            else:
                # Exclude everything from the Windows directory by default.
                # .. sometimes realpath changes the case of libname, lower it
                # .. use normpath because msys2 uses / instead of \
                fn = os.path.normpath(os.path.realpath(libname).lower())
                return fn.startswith(self._windows_dir)

    exclude_list = WinExcludeList(exclude_list)


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

    from macholib import util
    from macholib.MachO import MachO

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
        with open(dll.filename, 'rb+') as f:
            for header in dll.headers:
                f.seek(0)
                dll.write(f)
            f.seek(0, 2)
            f.flush()
    except Exception:
        pass
