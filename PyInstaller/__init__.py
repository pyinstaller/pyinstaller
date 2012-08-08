#
# Copyright (C) 2011 by Hartmut Goebel
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA

__all__ = ('HOMEPATH', 'CONFIGDIR', 'PLATFORM',
           'VERSION', 'get_version',
           'is_py23', 'is_py24', 'is_py25', 'is_py26', 'is_py27',
           'is_win', 'is_cygwin', 'is_darwin', 'is_unix', 'is_linux',
           'is_solar', 'is_aix')

import os
import sys

# Fail hard if Python does not have minimum required version
if sys.version_info < (2, 3):
    raise SystemExit('PyInstaller requires at least Python 2.3, sorry.')

# Extend PYTHONPATH with 3rd party libraries bundled with PyInstaller.
# (otherwise e.g. macholib won't work on Mac OS X)
from PyInstaller import lib
sys.path.insert(0, lib.__path__[0])

from PyInstaller import compat
from PyInstaller.utils import git

VERSION = (2, 0, 0)


is_py23 = compat.is_py23
is_py24 = compat.is_py24
is_py25 = compat.is_py25
is_py26 = compat.is_py26
is_py27 = compat.is_py27

is_win = compat.is_win
is_cygwin = compat.is_cygwin
is_darwin = compat.is_darwin

is_linux = compat.is_linux
is_solar = compat.is_solar
is_aix = compat.is_aix

is_unix = compat.is_unix


HOMEPATH = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

if is_win:
    CONFIGDIR = compat.getenv('APPDATA')
    if not CONFIGDIR:
        CONFIGDIR = os.path.expanduser('~\\Application Data')
elif is_darwin:
    CONFIGDIR = os.path.expanduser('~/Library/Application Support')
else:
    # According to XDG specification
    # http://standards.freedesktop.org/basedir-spec/basedir-spec-latest.html
    CONFIGDIR = compat.getenv('XDG_DATA_HOME')
    if not CONFIGDIR:
        CONFIGDIR = os.path.expanduser('~/.local/share')
CONFIGDIR = os.path.join(CONFIGDIR, 'pyinstaller')

PLATFORM = compat.system() + '-' + compat.architecture()

# path extensions for module seach
# :fixme: this should not be a global variable
__pathex__ = []


def get_version():
    version = '%s.%s' % (VERSION[0], VERSION[1])
    if VERSION[2]:
        version = '%s.%s' % (version, VERSION[2])
    if len(VERSION) >= 4 and VERSION[3]:
        version = '%s%s' % (version, VERSION[3])
        # include git revision in version string
        if VERSION[3] == 'dev' and VERSION[4] > 0:
            version = '%s-%s' % (version, VERSION[4])
    return version
