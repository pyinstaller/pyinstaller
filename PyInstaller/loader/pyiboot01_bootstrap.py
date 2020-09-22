#-----------------------------------------------------------------------------
# Copyright (c) 2005-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------


### Start bootstrap process
# Only python built-in modules can be used.

import sys
import pyimod03_importers

# Extend Python import machinery by adding PEP302 importers to sys.meta_path.
pyimod03_importers.install()


### Bootstrap process is complete.
# We can use other python modules (e.g. os)


import os


# Let other python modules know that the code is running in frozen mode.
if not hasattr(sys, 'frozen'):
    sys.frozen = True

# sys._MEIPASS is now set in the bootloader. Hooray.


# Python 3 C-API function Py_SetPath() resets sys.prefix to empty string.
# Python 2 was using PYTHONHOME for sys.prefix. Let's do the same for Python 3.
sys.prefix = sys._MEIPASS
sys.exec_prefix = sys.prefix


# Python 3.3+ defines also sys.base_prefix. Let's set them too.
sys.base_prefix = sys.prefix
sys.base_exec_prefix = sys.exec_prefix


# Some packages behaves differently when running inside virtual environment.
# E.g. IPython tries to append path VIRTUAL_ENV to sys.path.
# For the frozen app we want to prevent this behavior.
VIRTENV = 'VIRTUAL_ENV'
if VIRTENV in os.environ:
    # On some platforms (e.g. AIX) 'os.unsetenv()' is not available and then
    # deleting the var from os.environ does not delete it from the environment.
    os.environ[VIRTENV] = ''
    del os.environ[VIRTENV]


# Ensure sys.path contains absolute paths. Otherwise import of other python
# modules will fail when current working directory is changed by frozen
# application.
python_path = []
for pth in sys.path:
    python_path.append(os.path.abspath(pth))
    sys.path = python_path


# Implement workaround for prints in non-console mode. In non-console mode
# (with "pythonw"), print randomly fails with "[errno 9] Bad file descriptor"
# when the printed text is flushed (eg: buffer full); this is because the
# sys.stdout object is bound to an invalid file descriptor.
# Python 3000 has a fix for it (http://bugs.python.org/issue1415), but we
# feel that a workaround in PyInstaller is a good thing since most people
# found this problem for the first time with PyInstaller as they don't
# usually run their code with "pythonw" (and it's hard to debug anyway).
class NullWriter:
    softspace = 0
    encoding = 'UTF-8'

    def write(*args):
        pass

    def flush(*args):
        pass

    # Some packages are checking if stdout/stderr is available.
    # e.g. youtube-dl  for details see #1883
    def isatty(self):
        return False


# sys.stdout/err is None in GUI mode on Windows.
if sys.stdout is None:
    sys.stdout = NullWriter()
if sys.stderr is None:
    sys.stderr = NullWriter()


# At least on Windows, Python seems to hook up the codecs on this
# import, so it's not enough to just package up all the encodings.
#
# It was also reported that without 'encodings' module the frozen executable
# will fail to load in some configurations:
#
# http://www.pyinstaller.org/ticket/651
#
# Import 'encodings' module in a run-time hook is not enough since some
# run-time hooks require this module and the order of running code from
# from run-time hooks is not defined.
try:
    import encodings
except ImportError:
    pass


# In the Python interpreter 'warnings' module is imported when 'sys.warnoptions'
# is not empty. Mimic this behavior in PyInstaller.
if sys.warnoptions:
    import warnings

try:
    import ctypes
    import os
    from ctypes import LibraryLoader, DEFAULT_MODE

    def _frozen_name(name):
        if name:
            frozen_name = os.path.join(sys._MEIPASS, os.path.basename(name))
            if os.path.exists(frozen_name) and not os.path.isdir(frozen_name):
                name = frozen_name
        return name

    class PyInstallerImportError(OSError):
        def __init__(self, name):
            self.msg = ("Failed to load dynlib/dll %r. "
                        "Most probably this dynlib/dll was not found "
                        "when the application was frozen.") % name
            self.args = (self.msg,)

    class PyInstallerCDLL(ctypes.CDLL):
        def __init__(self, name, *args, **kwargs):
            name = _frozen_name(name)
            try:
                super(PyInstallerCDLL, self).__init__(name, *args, **kwargs)
            except Exception as base_error:
                raise PyInstallerImportError(name) from base_error

    ctypes.CDLL = PyInstallerCDLL
    ctypes.cdll = LibraryLoader(PyInstallerCDLL)

    class PyInstallerPyDLL(ctypes.PyDLL):
        def __init__(self, name, *args, **kwargs):
            name = _frozen_name(name)
            try:
                super(PyInstallerPyDLL, self).__init__(name, *args, **kwargs)
            except Exception as base_error:
                raise PyInstallerImportError(name) from base_error

    ctypes.PyDLL = PyInstallerPyDLL
    ctypes.pydll = LibraryLoader(PyInstallerPyDLL)

    if sys.platform.startswith('win'):
        class PyInstallerWinDLL(ctypes.WinDLL):
            def __init__(self, name,*args, **kwargs):
                name = _frozen_name(name)
                try:
                    super(PyInstallerWinDLL, self).__init__(name, *args, **kwargs)
                except Exception as base_error:
                    raise PyInstallerImportError(name) from base_error

        ctypes.WinDLL = PyInstallerWinDLL
        ctypes.windll = LibraryLoader(PyInstallerWinDLL)

        class PyInstallerOleDLL(ctypes.OleDLL):
            def __init__(self, name,*args, **kwargs):
                name = _frozen_name(name)
                try:
                    super(PyInstallerOleDLL, self).__init__(name, *args, **kwargs)
                except Exception as base_error:
                    raise PyInstallerImportError(name) from base_error

        ctypes.OleDLL = PyInstallerOleDLL
        ctypes.oledll = LibraryLoader(PyInstallerOleDLL)
except ImportError:
    pass

# On Mac OS X insert sys._MEIPASS in the first position of the list of paths
# that ctypes uses to search for libraries.
#
# Note: 'ctypes' module will NOT be bundled with every app because code in this
#       module is not scanned for module dependencies. It is safe to wrap
#       'ctypes' module into 'try/except ImportError' block.
if sys.platform.startswith('darwin'):
    try:
        from ctypes.macholib import dyld
        dyld.DEFAULT_LIBRARY_FALLBACK.insert(0, sys._MEIPASS)
    except ImportError:
        # Do nothing when module 'ctypes' is not available.
        pass


# Make .eggs and zipfiles available at runtime
d = "eggs"
d = os.path.join(sys._MEIPASS, d)
# Test if the 'eggs' directory exists. This allows to
# opportunistically including this script into the packaged exe, even
# if no eggs as found when packaging the program. (Which may be a
# use-case, see issue #653.
if os.path.isdir(d):
    for fn in os.listdir(d):
        sys.path.append(os.path.join(d, fn))
