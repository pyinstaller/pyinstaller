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
# Python there is mostly 64bit.


import os


try:
    import PyInstaller
except ImportError:
    # if importing PyInstaller fails, try to load from parent
    # directory to support running without installation
    import imp
    if not hasattr(os, "getuid") or os.getuid() != 0:
        imp.load_module('PyInstaller', *imp.find_module('PyInstaller',
            [os.path.dirname(os.path.dirname(os.path.abspath(__file__)))]))


import PyInstaller.compat as compat


_PACKAGES = [
    'docutils',
    'jinja2',
    'MySQL-python',
    'numpy ',
    'PIL',
    'pycrypto',
    #'pyenchant',
    'pyodbc',
    'pytz',
    'sphinx',
    'simplejson',
    'SQLAlchemy',
    #'wxPython',
]


def main():
    for pkg in _PACKAGES:
        print 'Installing module... %s' % pkg
        retcode = compat.exec_command_rc('pip', 'install', pkg)
        if retcode:
            print '  %s installation failed' % pkg


if __name__ == '__main__':
    main()
