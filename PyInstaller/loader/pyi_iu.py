#
# Copyright (C) 2005-2011, Giovanni Bajo
#
# Based on previous work under copyright (c) 2002 McMillan Enterprises, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# In addition to the permissions in the GNU General Public License, the
# authors give you unlimited permission to link or embed the compiled
# version of this file into combinations with other programs, and to
# distribute those combinations without any restriction coming from the
# use of this file. (The General Public License restrictions do apply in
# other respects; for example, they cover modification of the file, and
# distribution when not linked into a combine executable.)
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA
#


# TODO Rename this module to  'pyi_os_path.py' Since this module will then only wrap functions from modules 'os' and 'os.path'. And all Owner classes will be removed.


### **NOTE** This module is used during bootstrap.
### Import *ONLY* builtin modules.
### List of built-in modules: sys.builtin_module_names
import sys
import imp


# TODO Is this function still used anywhere?
def getDescr(fnm):
    ext = getpathext(fnm)
    for (suffix, mode, typ) in imp.get_suffixes():
        if suffix == ext:
            return (suffix, mode, typ)


# Some helper functions.


def packagename(s):
    """
    For package name like 'module.submodule.subsubmodule' returns
    'module.submodule'. If name does not contain any dots '.',
    empty string '' is returned.
    """
    i = s.rfind('.')
    if i >= 0:
        return s[:i]
    else:
        return ''


def namesplit(s):
    """
    Split package name at the position of dot '.'.

    Examples:
        'module.submodule' =>  ['module', 'submodule']
        'module'           =>  ['module']
        ''                 =>  []
    """
    rslt = []
    # Ensure that for empty string '' an empty list is returned.
    if s:
        rslt = s.split('.')
    return rslt


def getpathext(fnm):
    i = fnm.rfind('.')
    if i >= 0:
        return fnm[i:]
    else:
        return ''


def pathisdir(pathname):
    "Local replacement for os.path.isdir()."
    try:
        s = _os_stat(pathname)
    except OSError:
        return None
    return (s[0] & 0170000) == 0040000


_os_stat = _os_path_join = _os_getcwd = _os_path_dirname = None
_os_environ = _os_listdir = _os_path_basename = None
_os_sep = None


def _os_bootstrap():
    """
    Set up 'os' module replacement functions for use during import bootstrap.
    """

    global _os_stat, _os_getcwd, _os_environ, _os_listdir
    global _os_path_join, _os_path_dirname, _os_path_basename
    global _os_sep

    names = sys.builtin_module_names

    join = dirname = environ = listdir = basename = None
    mindirlen = 0
    # Only 'posix' and 'nt' os specific modules are supported.
    # 'dos', 'os2' and 'mac' (MacOS 9) are not supported.
    if 'posix' in names:
        from posix import stat, getcwd, environ, listdir
        sep = _os_sep = '/'
        mindirlen = 1
    elif 'nt' in names:
        from nt import stat, getcwd, environ, listdir
        sep = _os_sep = '\\'
        mindirlen = 3
    else:
        raise ImportError('no os specific module found')

    if join is None:
        def join(a, b, sep=sep):
            if a == '':
                return b
            lastchar = a[-1:]
            if lastchar == '/' or lastchar == sep:
                return a + b
            return a + sep + b

    if dirname is None:
        def dirname(a, sep=sep, mindirlen=mindirlen):
            for i in range(len(a) - 1, -1, -1):
                c = a[i]
                if c == '/' or c == sep:
                    if i < mindirlen:
                        return a[:i + 1]
                    return a[:i]
            return ''

    if basename is None:
        if sys.platform.startswith('win'):
            # Implementation from ntpath.py module
            # from standard Python 2.7 Library.
            def basename(pth):
                ## Implementation of os.path.splitdrive()
                if pth[1:2] == ':':
                    d = pth[0:2]
                    p = pth[2:]
                else:
                    d = ''
                    p = pth
                ## Implementation of os.path.split()
                # set i to index beyond p's last slash
                i = len(p)
                while i and p[i - 1] not in '/\\':
                    i = i - 1
                head, tail = p[:i], p[i:]  # now tail has no slashes
                # Windows implementation is based on split(). We need
                # to return only tail.
                return tail
        else:
            # Implementation from ntpath.py module
            # from standard Python 2.7 Library.
            def basename(pth):
                i = pth.rfind('/') + 1
                return pth[i:]

    def _listdir(dir, cache=None):
        # The cache is not used. It was found to cause problems
        # with programs that dynamically add python modules to be
        # reimported by that same program (i.e., plugins), because
        # the cache is only built once at the beginning, and never
        # updated. So, we must really list the directory again.
        return listdir(dir)

    _os_stat = stat
    _os_getcwd = getcwd
    _os_path_join = join
    _os_path_dirname = dirname
    _os_environ = environ
    _os_listdir = _listdir
    _os_path_basename = basename


_os_bootstrap()


if 'PYTHONCASEOK' not in _os_environ:
    def caseOk(filename):
        files = _os_listdir(_os_path_dirname(filename))
        return _os_path_basename(filename) in files
else:
    def caseOk(filename):
        return True
