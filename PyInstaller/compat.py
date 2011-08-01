#! /usr/bin/env python
#
# Various classes and functions to provide some backwards-compatibility
# with previous versions of Python from 2.3 onward.
#
# Copyright (C) 2011, Martin Zibricky
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA

import os
import sys


try:
    # Python 2.5+
    import hashlib
except ImportError:
    import md5
    import sha

    class _Hash(object):
        def __init__(self):
            self.md5 = md5.new
            self.sha = sha.new
    hashlib = _Hash()


def architecture():
    """
    Returns the bit depth of the python interpreter's architecture as
    a string ('32bit' or '64bit'). Similar to platform.architecture(),
    but with fixes for universal binaries on MacOS.
    """
    try:
        # Python 2.3+
        import platform
        if sys.platform == 'darwin':
            # Darwin's platform.architecture() is buggy and always
            # returns "64bit" event for the 32bit version of Python's
            # universal binary. So we roll out our own (that works
            # on Darwin).
            if sys.maxint > 2L ** 32:
                return '64bit'
            else:
                return '32bit'
        else:
            return platform.architecture()[0]
    except ImportError:
        return '32bit'


def system():
    try:
        # Python 2.3+
        import platform
        # On some Windows installation (Python 2.4) platform.system() is
        # broken and incorrectly returns 'Microsoft' instead of 'Windows'.
        # http://mail.python.org/pipermail/patches/2007-June/022947.html
        syst = platform.system()
        return {'Microsoft': 'Windows'}.get(syst, syst)
    except ImportError:
        n = {'nt': 'Windows', 'linux2': 'Linux', 'darwin': 'Darwin'}
        return n[os.name]


# Set and get environment variables does not handle unicode strings correctly
# on Windows.


def getenv(name):
    """
    Returns unicode string containing value of environment variable 'name'.
    """
    pass


def setenv(name, value):
    """
    Accepts unicode string and set it as environment variable 'name' containing
    value 'value'.
    """
    pass


# Wrap creating subprocesses
# We might decide to use subprocess module instead os.system()


def exec_command(cmd):
    pass
