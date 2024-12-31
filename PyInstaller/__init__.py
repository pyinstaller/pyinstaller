#-----------------------------------------------------------------------------
# Copyright (c) 2005-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

__all__ = ('HOMEPATH', 'PLATFORM', '__version__', 'DEFAULT_DISTPATH', 'DEFAULT_SPECPATH', 'DEFAULT_WORKPATH')

import os

from PyInstaller import compat

# Note: Keep this variable as plain string so it could be updated automatically when doing a release.
__version__ = '6.11.1'

# Absolute path of this package's directory. Save this early so all submodules can use the absolute path. This is
# required for example if the current directory changes prior to loading the hooks.
PACKAGEPATH = os.path.abspath(os.path.dirname(__file__))

HOMEPATH = os.path.dirname(PACKAGEPATH)

# Default values of paths where to put files created by PyInstaller. If changing these, do not forget to update the
# help text for corresponding command-line options, defined in build_main.

# Where to put created .spec file.
DEFAULT_SPECPATH = os.getcwd()
# Where to put the final frozen application.
DEFAULT_DISTPATH = os.path.join(os.getcwd(), 'dist')
# Where to put all the temporary files; .log, .pyz, etc.
DEFAULT_WORKPATH = os.path.join(os.getcwd(), 'build')

PLATFORM = compat.system + '-' + compat.architecture
# Include machine name in path to bootloader for some machines (e.g., 'arm'). Explicitly avoid doing this on macOS,
# where we keep universal2 bootloaders in Darwin-64bit folder regardless of whether we are on x86_64 or arm64.
if compat.machine and not compat.is_darwin:
    PLATFORM += '-' + compat.machine
# Similarly, disambiguate musl Linux from glibc Linux.
if compat.is_musl:
    PLATFORM += '-musl'
