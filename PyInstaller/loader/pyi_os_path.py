#
# Copyright (C) 2012, Martin Zibricky
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


### **NOTE** This module is used during bootstrap.
### Import *ONLY* builtin modules.
### List of built-in modules: sys.builtin_module_names


# Set up 'os' and 'os.path' module replacement functions for use during import
# bootstrap.


import sys


_builtin_names = sys.builtin_module_names
_mindirlen = 0


# Wrap os.environ, os.listdir(), os.sep

# We cannot cache the content of os.listdir(). It was found to cause problems
# with programs that dynamically add python modules to be reimported by that
# same program (i.e., plugins), because the cache is only built once
# at the beginning, and never updated. So, we must really list the directory
# again.

if 'posix' in _builtin_names:  # For Linux, Unix, Mac OS X
    from posix import environ as os_environ
    from posix import listdir as os_listdir
    os_sep = '/'
    _mindirlen = 1
elif 'nt' in _builtin_names:  # For Windows
    from nt import environ as os_environ
    from nt import listdir as os_listdir
    os_sep = '\\'
    _mindirlen = 3
else:
    raise ImportError('No os specific module found')


# Wrap os.path.join()
def os_path_join(a, b, sep=os_sep):
    if a == '':
        return b
    lastchar = a[-1:]
    if lastchar == '/' or lastchar == sep:
        return a + b
    return a + sep + b


# Wrap os.path.dirname()
def os_path_dirname(a, sep=os_sep, mindirlen=_mindirlen):
    for i in range(len(a) - 1, -1, -1):
        c = a[i]
        if c == '/' or c == sep:
            if i < mindirlen:
                return a[:i + 1]
            return a[:i]
    return ''


# Wrap os.path.basename()
if sys.platform.startswith('win'):
    # Implementation from ntpath.py module
    # from standard Python 2.7 Library.
    def os_path_basename(pth):
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
    def os_path_basename(pth):
        i = pth.rfind('/') + 1
        return pth[i:]


if 'PYTHONCASEOK' not in os_environ:
    def caseOk(filename):
        files = os_listdir(os_path_dirname(filename))
        return os_path_basename(filename) in files
else:
    def caseOk(filename):
        return True
