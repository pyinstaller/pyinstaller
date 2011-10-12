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

__all__ = ('HOMEPATH', 'CONFIGDIR', 'DEFAULT_CONFIGFILE', 'PLATFORM',
           'VERSION', 'get_version',
           'is_py23', 'is_py24', 'is_py25', 'is_py26', 'is_py27',
           'is_win', 'is_cygwin', 'is_darwin', 'is_unix', 'is_linux',
           'is_solar', 'is_aix')

import os
import sys

from PyInstaller import compat
from PyInstaller.utils import svn

VERSION = (1, 6, 0, 'dev', svn.get_svn_revision())

is_py23 = sys.version_info >= (2,3)
is_py24 = sys.version_info >= (2,4)
is_py25 = sys.version_info >= (2,5)
is_py26 = sys.version_info >= (2,6)
is_py27 = sys.version_info >= (2,7)

is_win = sys.platform.startswith('win')
is_cygwin = sys.platform == 'cygwin'
is_darwin = sys.platform == 'darwin'  # Mac OS X

# Unix platforms
is_linux = sys.platform == 'linux2'
is_solar = sys.platform.startswith('sun')  # Solaris
is_aix = sys.platform.startswith('aix')

# Some code parts are similar to several unix platforms
# (e.g. Linux, Solaris, AIX)
# Mac OS X is not considered as unix since there are many
# platform specific details for Mac in PyInstaller.
is_unix = is_linux or is_solar or is_aix

HOMEPATH = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

if is_win:
    CONFIGDIR = os.environ['APPDATA']
    if not CONFIGDIR:
        CONFIGDIR = os.path.expanduser('~\\Application Data')
elif is_darwin:
    CONFIGDIR = os.path.expanduser('~/Library/Application Support')
else:
    # According to XDG specification
    # http://standards.freedesktop.org/basedir-spec/basedir-spec-latest.html
    CONFIGDIR = os.environ.get('XDG_DATA_HOME', None)
    if CONFIGDIR is None:
        CONFIGDIR = os.path.expanduser('~/.local/share')
CONFIGDIR = os.path.join(CONFIGDIR, 'pyinstaller')

DEFAULT_CONFIGFILE = os.path.join(CONFIGDIR, 'config.dat')

PLATFORM = compat.system() + '-' + compat.architecture()

# path extensions for module seach
# :fixme: this should not be a global variable
__pathex__ = []

def get_version():
    version = '%s.%s' % (VERSION[0], VERSION[1])
    if VERSION[2]:
        version = '%s.%s' % (version, VERSION[2])
    if VERSION[3]:
        version = '%s%s' % (version, VERSION[3])
    # include svn revision in version string
    if VERSION[3] == 'dev' and VERSION[4] > 0:
        version = '%s%s' % (version, VERSION[4])
    return version
