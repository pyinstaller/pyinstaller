#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Install necessary 3rd party Python modules to run all tests.
# This script is supposed to be used in a continuous integration system:
# https://jenkins.shiningpanda.com/pyinstaller/
# Python there is mostly 64bit.


import os
import sys


# Expand PYTHONPATH with PyInstaller package to support running without
# installation.
pyi_home = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, pyi_home)


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
