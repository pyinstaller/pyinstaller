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


__all__ = ('HOMEPATH', 'PLATFORM', '__version__')

import os
import sys

from . import compat
from .utils.git import get_repo_revision


# Note: Keep this variable as plain string so it could be updated automatically
#       when doing a release.
__version__ = '4.0'


# Absolute path of this package's directory. Save this early so all
# submodules can use the absolute path. This is required e.g. if the
# current directory changes prior to loading the hooks.
PACKAGEPATH = os.path.abspath(os.path.dirname(__file__))

HOMEPATH = os.path.dirname(PACKAGEPATH)


# Update __version__ as necessary.
if os.path.exists(os.path.join(HOMEPATH, 'setup.py')):
    # PyInstaller is run directly from source without installation or
    # __version__ is called from 'setup.py' ...
    if compat.getenv('PYINSTALLER_DO_RELEASE') == '1':
        # Suppress the git revision when doing a release.
        pass
    elif 'sdist' not in sys.argv:
        # and 'setup.py' was not called with 'sdist' argument.
        # For creating source tarball we do not want git revision
        # in the filename.
        try:
            __version__ += get_repo_revision()
        except Exception:
            # Write to stderr because stdout is used for eval() statement
            # in some subprocesses.
            sys.stderr.write('WARN: failed to parse git revision')
else:
    # PyInstaller was installed by `python setup.py install'.
    import pkg_resources
    __version__ = pkg_resources.get_distribution('PyInstaller').version


## Default values of paths where to put files created by PyInstaller.
## Mind option-help in build_main when changes these
# Folder where to put created .spec file.
DEFAULT_SPECPATH = os.getcwd()
# Folder where to put created .spec file.
# Where to put the final app.
DEFAULT_DISTPATH = os.path.join(os.getcwd(), 'dist')
# Where to put all the temporary work files, .log, .pyz and etc.
DEFAULT_WORKPATH = os.path.join(os.getcwd(), 'build')


PLATFORM = compat.system + '-' + compat.architecture
# Include machine name in path to bootloader for some machines.
# e.g. 'arm'
if compat.machine:
    PLATFORM += '-' + compat.machine
