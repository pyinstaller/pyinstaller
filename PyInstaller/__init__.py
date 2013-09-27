#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


__all__ = ('HOMEPATH', 'CONFIGDIR', 'PLATFORM',
           'VERSION', 'get_version',
           'is_py25', 'is_py26', 'is_py27',
           'is_win', 'is_cygwin', 'is_darwin', 'is_unix', 'is_linux',
           'is_solar', 'is_aix')

import os
import sys


# Fail hard if Python does not have minimum required version
if sys.version_info < (2, 4):
    raise SystemExit('PyInstaller requires at least Python 2.4, sorry.')


# Extend PYTHONPATH with 3rd party libraries bundled with PyInstaller.
# (otherwise e.g. macholib won't work on Mac OS X)
from PyInstaller import lib
sys.path.insert(0, lib.__path__[0])


from PyInstaller import compat
from PyInstaller.utils import git

# Uncomment this line for development of version 3.0.
#VERSION = (3, 0, 0, 'dev', git.get_repo_revision())
VERSION = (2, 1, 0)


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


# This ensures PyInstaller will work on Windows with paths containing
# foreign characters.
HOMEPATH = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if is_win:
    try:
        unicode(HOMEPATH)
    except UnicodeDecodeError:
        # Do conversion to ShortPathName really only in case HOMEPATH is not
        # ascii only - conversion to unicode type cause this unicode error.
        try:
            import win32api
            HOMEPATH = win32api.GetShortPathName(HOMEPATH)
        except ImportError:
            pass


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


## Default values of paths where to put files created by PyInstaller.
# Folder where to put created .spec file.
DEFAULT_SPECPATH = compat.getcwd()
# Folder where to put created .spec file.
# Where to put the final app.
DEFAULT_DISTPATH = os.path.join(compat.getcwd(), 'dist')
# Where to put all the temporary work files, .log, .pyz and etc.
DEFAULT_WORKPATH = os.path.join(compat.getcwd(), 'build')


PLATFORM = compat.system() + '-' + compat.architecture()
# Include machine name in path to bootloader for some machines.
# e.g. 'arm'
if compat.machine():
    PLATFORM += '-' + compat.machine()


# path extensions for module seach
# FIXME this should not be a global variable
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
