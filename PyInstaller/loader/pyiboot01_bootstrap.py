#-----------------------------------------------------------------------------
# Copyright (c) 2005-2022, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

#-- Start bootstrap process
# Only python built-in modules can be used.

import sys

import pyimod02_importers

# Extend Python import machinery by adding PEP302 importers to sys.meta_path.
pyimod02_importers.install()

#-- Bootstrap process is complete.
# We can use other python modules (e.g. os)

import os  # noqa: E402

# Let other python modules know that the code is running in frozen mode.
if not hasattr(sys, 'frozen'):
    sys.frozen = True

# sys._MEIPASS is now set in the bootloader. Hooray.

# Python 3 C-API function Py_SetPath() resets sys.prefix to empty string. Python 2 was using PYTHONHOME for sys.prefix.
# Let's do the same for Python 3.
sys.prefix = sys._MEIPASS
sys.exec_prefix = sys.prefix

# Python 3.3+ defines also sys.base_prefix. Let's set them too.
sys.base_prefix = sys.prefix
sys.base_exec_prefix = sys.exec_prefix

# Some packages behave differently when running inside virtual environment. E.g., IPython tries to append path
# VIRTUAL_ENV to sys.path. For the frozen app we want to prevent this behavior.
VIRTENV = 'VIRTUAL_ENV'
if VIRTENV in os.environ:
    # On some platforms (e.g., AIX) 'os.unsetenv()' is unavailable and deleting the var from os.environ does not
    # delete it from the environment.
    os.environ[VIRTENV] = ''
    del os.environ[VIRTENV]

# Ensure sys.path contains absolute paths. Otherwise, import of other python modules will fail when current working
# directory is changed by the frozen application.
python_path = []
for pth in sys.path:
    python_path.append(os.path.abspath(pth))
    sys.path = python_path


# Implement workaround for prints in non-console mode. In non-console mode (with "pythonw"), print randomly fails with
# "[errno 9] Bad file descriptor" when the printed text is flushed (e.g., buffer full); this is because the sys.stdout
# object is bound to an invalid file descriptor.
# Python 3000 has a fix for it (http://bugs.python.org/issue1415), but we feel that a workaround in PyInstaller is a
# good thing, because most people first encounter this problem with PyInstaller as they do not usually run their code
# with "pythonw" (and it is difficult to debug, anyway).
class NullWriter:
    softspace = 0
    encoding = 'UTF-8'

    def write(*args):
        pass

    def flush(*args):
        pass

    # Some packages are checking if stdout/stderr is available (e.g., youtube-dl). For details, see #1883.
    def isatty(self):
        return False


# sys.stdout/err is None in GUI mode on Windows.
if sys.stdout is None:
    sys.stdout = NullWriter()
if sys.stderr is None:
    sys.stderr = NullWriter()

# At least on Windows, Python seems to hook up the codecs on this import, so it is not enough to just package up all
# the encodings.
#
# It was also reported that without 'encodings' module, the frozen executable fails to load in some configurations:
# http://www.pyinstaller.org/ticket/651
#
# Importing 'encodings' module in a run-time hook is not enough, since some run-time hooks require this module, and the
# order of running the code from the run-time hooks is not defined.
try:
    import encodings  # noqa: F401
except ImportError:
    pass

# In the Python interpreter 'warnings' module is imported when 'sys.warnoptions' is not empty. Mimic this behavior.
if sys.warnoptions:
    import warnings  # noqa: F401

# Install the hooks for ctypes
import pyimod03_ctypes  # noqa: E402

pyimod03_ctypes.install()

# Make .eggs and zipfiles available at runtime
d = "eggs"
d = os.path.join(sys._MEIPASS, d)
# Test if the 'eggs' directory exists. This allows us to opportunistically include this script into the packaged exe,
# even if no eggs were found when packaging the program. (Which may be a use-case, see issue #653).
if os.path.isdir(d):
    for fn in os.listdir(d):
        sys.path.append(os.path.join(d, fn))
