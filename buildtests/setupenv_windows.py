#
# Copyright (C) 2012, Martin Zibricky
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA


# Install necessary 3rd party Python modules to run all tests.
# This script is supposed to be used in a continuous integration system:
# https://jenkins.shiningpanda.com/pyinstaller/


import platform
import sys

# easy_install command used in a Python script.
from setuptools.command import easy_install


PYVER = (sys.version_info[0], sys.version_info[1])


def pywin32_architecture():
    mapping = {'32bit': 'win32', '64bit': 'win-amd64'}
    arch = platform.architecture()[0]
    return mapping[arch]


_PACKAGES = {
    # 'modulename': 'pypi_name_or_url'
    'win32api': 'http://downloads.sourceforge.net/project/pywin32/pywin32/Build%%20217/pywin32-217.%s-py%d.%d.exe' %
        (pywin32_architecture(), sys.version_info[0], sys.version_info[1]),
    'simplejson': 'simplejson',
    'sqlalchemy': 'sqlalchemy',
}

_PY_VERSION = {
    'simplejson': (2, 5),
    'sqlalchemy': (2, 4),
}


def main():
    # Install packages.
    for k, v in _PACKAGES.items():
        # Test python version for module.
        if k in _PY_VERSION:
            # Python version too old, skip module.
            if PYVER < _PY_VERSION[k]:
                continue
        try:
            __import__(k)
            print 'Skipping module... %s' % k
        # Module is not available - install it.
        except ImportError:
            easy_install.main([v])


if __name__ == '__main__':
    main()
