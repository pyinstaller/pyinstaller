#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


### **NOTE** This module is used during bootstrap.
### Import *ONLY* builtin modules.
### List of built-in modules: sys.builtin_module_names


"""
Set up 'os' and 'os.path' module replacement functions for use during import
bootstrap.
"""


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
