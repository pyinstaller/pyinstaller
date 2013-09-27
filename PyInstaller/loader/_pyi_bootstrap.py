#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


### Start bootstrap process
# Only python built-in modules can be used.

import sys

import pyi_os_path
import pyi_archive
import pyi_importers

# Extend Python import machinery by adding PEP302 importers to sys.meta_path.
pyi_importers.install()


### Bootstrap process is complete.
# We can use other python modules (e.g. os)


import os


# Let other python modules know that the code is running in frozen mode.
if not hasattr(sys, 'frozen'):
    sys.frozen = True


# Now that the startup is complete, we can reset the _MEIPASS2 env
# so that if the program invokes another PyInstaller one-file program
# as subprocess, this subprocess will not fooled into thinking that it
# is already unpacked.
#
# But we need to preserve _MEIPASS2 value for cases where reseting it
# causes some issues (e.g. multiprocess module on Windows).
# set  sys._MEIPASS
MEIPASS2 = '_MEIPASS2'
if MEIPASS2 in os.environ:
    meipass2_value = os.environ[MEIPASS2]

    # Ensure sys._MEIPASS is absolute path.
    meipass2_value = os.path.abspath(meipass2_value)
    sys._MEIPASS = meipass2_value

    # Delete _MEIPASS2 from environment.
    # On some platforms (e.g. AIX) 'os.unsetenv()' is not available and then
    # deleting the var from os.environ does not delete it from the environment.
    # In those cases we cannot delete the variable but only set it to the
    # empty string.
    os.environ[MEIPASS2] = ''
    del os.environ[MEIPASS2]


# Some packages behaves differently when running inside virtual environment.
# E.g. IPython tries to append path VIRTUAL_ENV to sys.path.
# For the frozen app we want to prevent this behavior.
VIRTENV = 'VIRTUAL_ENV'
if VIRTENV in os.environ:
    # On some platforms (e.g. AIX) 'os.unsetenv()' is not available and then
    # deleting the var from os.environ does not delete it from the environment.
    os.environ[VIRTENV] = ''
    del os.environ[VIRTENV]


# Forces PyInstaller to include fake 'site' module. Fake 'site' module
# is dummy and does not do any search for additional Python modules.
import site


# Ensure PYTHONPATH contains absolute paths. Otherwise import of other python
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
    def write(*args):
        pass

    def flush(*args):
        pass


if sys.stdout.fileno() < 0:
    sys.stdout = NullWriter()
if sys.stderr.fileno() < 0:
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
