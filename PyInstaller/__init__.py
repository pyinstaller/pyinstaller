#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


__all__ = ('HOMEPATH', 'CONFIGDIR', 'PLATFORM',
           'VERSION', 'get_version')

import os
import sys


# Fail hard if Python does not have minimum required version
if sys.version_info < (2, 7):
    raise SystemExit('PyInstaller requires at least Python 2.7, sorry.')


# Extend PYTHONPATH with 3rd party libraries bundled with PyInstaller.
# (otherwise e.g. macholib won't work on Mac OS X)
#
# Append lib directory at the end of sys.path and not at the beginning.
# Python will first try necessary libraries from the system and fallback
# to the lib directory.
#
# Some users complained that PyInstaller failed because their apps were
# using too old versions of some libraries that PyInstaller uses too.
from PyInstaller import lib
sys.path.append(lib.__path__[0])


from PyInstaller import compat
from PyInstaller.compat import is_darwin, is_win, is_py2
from PyInstaller.utils import git


# Fail hard if Python on Windows does not have pywin32 installed.
if is_win:
    try:
        from PyInstaller.utils.win32 import winutils
        pywintypes = winutils.import_pywin32_module('pywintypes')
    except ImportError:
        raise SystemExit('PyInstaller cannot check for assembly dependencies.\n'
                         'Please install PyWin32.\n'
                         'http://sourceforge.net/projects/pywin32/')


VERSION = (3, 0, 0, 'dev', git.get_repo_revision())


# This ensures for Python 2 that PyInstaller will work on Windows with paths
# containing foreign characters.
HOMEPATH = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if is_win and is_py2:
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
        if VERSION[3] == 'dev' and len(VERSION) >= 5 and len(VERSION[4]) > 0:
            version = '%s-%s' % (version, VERSION[4])
    return version
