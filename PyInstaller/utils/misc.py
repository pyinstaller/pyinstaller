#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
This module is for the miscellaneous routines which do not fit somewhere else.
"""

import glob
import os

from PyInstaller import log as logging
from PyInstaller.compat import is_win

logger = logging.getLogger(__name__)


def dlls_in_subdirs(directory):
    """Returns *.dll, *.so, *.dylib in given directories and subdirectories."""
    files = []
    for root, dirs, files in os.walk(directory):
        files.extend(dlls_in_dir(root))


def dlls_in_dir(directory):
    """Returns *.dll, *.so, *.dylib in given directory."""
    files = []
    files.extend(glob.glob(os.path.join(directory, '*.so')))
    files.extend(glob.glob(os.path.join(directory, '*.dll')))
    files.extend(glob.glob(os.path.join(directory, '*.dylib')))
    return files


def find_executable(executable, path=None):
    """
    Try to find 'executable' in the directories listed in 'path' (a
    string listing directories separated by 'os.pathsep'; defaults to
    os.environ['PATH']).

    Returns the complete filename or None if not found.

    Code from http://snippets.dzone.com/posts/show/6313
    """
    if path is None:
        path = os.environ['PATH']
    paths = path.split(os.pathsep)
    extlist = ['']

    if is_win:
        (base, ext) = os.path.splitext(executable)
        # Executable files on windows have an arbitrary extension, but
        # .exe is automatically appended if not present in the name.
        if not ext:
            executable = executable + ".exe"
        pathext = os.environ['PATHEXT'].lower().split(os.pathsep)
        (base, ext) = os.path.splitext(executable)
        if ext.lower() not in pathext:
            extlist = pathext

    for ext in extlist:
        execname = executable + ext
        if os.path.isfile(execname):
            return execname
        else:
            for p in paths:
                f = os.path.join(p, execname)
                if os.path.isfile(f):
                    return f
    else:
        return None


def get_unicode_modules():
    """
    Try importing codecs and encodings to include unicode support
    in created binary.
    """
    modules = []
    try:
        import codecs
        modules = ['codecs']
        import encodings
        # `encodings` imports `codecs`, so only the first is required.
        modules = ['encodings']
    except ImportError:
        pass
    return modules


def get_code_object(filename):
    """
    Convert source code from Python source file to code object.
    """
    try:
        source_code_string = open(filename, 'rU').read() + '\n'
        code_object = compile(source_code_string, filename, 'exec')
        return code_object
    except SyntaxError, e:
        logger.exception(e)
        raise SystemExit(10)


def get_path_to_toplevel_modules(filename):
    """
    Return the path to top-level directory that contains Python modules.

    It will look in parent directories for __init__.py files. The first parent
    directory without __init__.py is the top-level directory.

    Returned directory might be used to extend the PYTHONPATH.
    """
    curr_dir = os.path.dirname(os.path.abspath(filename))
    pattern = '__init__.py'

    # Try max. 10 levels up.
    try:
        for i in range(10):
            files = set(os.listdir(curr_dir))
            # 'curr_dir' is still not top-leve go to parent dir.
            if pattern in files:
                curr_dir = os.path.dirname(curr_dir)
            # Top-level dir found - return it.
            else:
                return curr_dir
    except IOError:
        pass
    # No top-level directory found or any error.
    return None
