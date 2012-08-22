# Copyright (C) 2005-2011, Giovanni Bajo
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


### Start bootstrap process
# Only python built-in modules can be used.

import sys

import pyi_archive
import pyi_iu

# Force Python to look first for modules bundled in the executable created
# PyInstaller.
pyi_iu._globalownertypes.insert(0, pyi_archive.PYZOwner)

# Override default import manager in Python
sys.importManager = pyi_iu.ImportManager()
sys.importManager.install()


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


# Ensure PYTHONHOME environment variable is unset. PYTHONHOME
# makes sure that no python modules from host OS are used. Startup is
# By deleting it we ensure that invoked standard Python interpreter
# is not affected by PYTHONHOME from bootloader.
if 'PYTHONHOME' in os.environ:
    # On some platforms (e.g. AIX) 'os.unsetenv()' is not available and then
    # deleting the var from os.environ does not delete it from the environment.
    # In those cases we cannot delete the variable but only set it to the
    # empty string.
    os.environ['PYTHONHOME'] = ''
    del os.environ['PYTHONHOME']
# FIXME On Windows setting environment variable PYTHONHOME does not work.
# This is a workaround for that. PYTHONHOME should be fixed for Windows
# in bootloader.
# http://www.pyinstaller.org/ticket/549
else:
    sys.prefix = sys._MEIPASS
    sys.exec_prefix = sys._MEIPASS


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
