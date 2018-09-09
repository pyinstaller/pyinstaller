#-----------------------------------------------------------------------------
# Copyright (c) 2013-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Install necessary 3rd party Python modules to run all tests.
# This script is supposed to be used in a continuous integration system:
# https://jenkins.shiningpanda.com/pyinstaller/
# Python there is mostly 64bit. Only Python 2.4 is 32bit on Windows 7.

from __future__ import print_function

import glob
import optparse
import os
import platform
import sys

# easy_install command used in a Python script.
from setuptools.command import easy_install


# Expand PYTHONPATH with PyInstaller package to support running without
# installation -- only if not running in a virtualenv.
if not hasattr(sys, 'real_prefix'):
    pyi_home = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
    sys.path.insert(0, pyi_home)


from PyInstaller.compat import is_py2


PYVER = '.'.join([str(x) for x in sys.version_info[0:2]])


def py_arch():
    """
    .exe installers of Python modules contain architecture name in filename.
    """
    mapping = {'32bit': 'win32', '64bit': 'win-amd64'}
    arch = platform.architecture()[0]
    return mapping[arch]


# Pick a PyCrypto version to use to test bytecode encryption. This is typically
# used in conjunction with continuous integration.
if 'PYCRYPTO_VERSION' in os.environ:
    pycrypto = 'PyCrypto==%s' % os.environ['PYCRYPTO_VERSION']
else:
    pycrypto = 'PyCrypto'


_PACKAGES = {
    # 'modulename': 'pypi_name_or_url_or_path'
    'docutils': ['docutils'],
    'IPython': ['IPython'],
    'jinja2': ['jinja2'],
    'keyring': ['keyring'],
    'markdown': ['markdown'],
    'MySQLdb': ['MySQL-python-*%s-py%s.exe' % (py_arch(), PYVER)],
    'numpy': ['numpy-unoptimized-*%s-py%s.exe' % (py_arch(), PYVER)],
    'PIL': ['PIL-*%s-py%s.exe' % (py_arch(), PYVER)],
    'pycparser': ['pycparser'],
    'PyCrypto': [pycrypto],
    'psycopg2': ['psycopg2-*%s-py%s.exe' % (py_arch(), PYVER)],
    'pyexcelerate': ['pyexcelerate'],
    'pylint': ['pylint'],
    'pyodbc': ['pyodbc'],
    'pyttsx': ['pyttsx'],
    'pytz': ['pytz'],
    'pyusb': ['pyusb'], # package usb
    'qt4reactor': ['qt4reactor'],
    'requests': ['requests'],
    'scapy': ['scapy'],
    #'simplejson': ['simplejson'],
    'sphinx': ['sphinx'],
    'sqlalchemy': ['SQLAlchemy-*%s-py%s.exe' % (py_arch(), PYVER)],
    'twisted': ['twisted'],
    'wx': ['wxPython-common-*%s-py%s.exe' % (py_arch(), PYVER),
        'wxPython-2*%s-py%s.exe' % (py_arch(), PYVER)],
    # PyWin32 is installed on ShiningPanda hosting.
    'win32api': ['http://downloads.sourceforge.net/project/pywin32/pywin32/Build%%20217/pywin32-217.%s-py%s.exe' %
        (py_arch(), PYVER)],
}

_PY_VERSION = {
    'keyring': is_py2,
    'MySQLdb': is_py2,
    'numpy': is_py2,
    'PIL': is_py2,
    'psycopg2': is_py2,
    'simplejson': is_py2,
    'twisted': is_py2,  # wheels are avalable for 2.7 only
    # Installers are available only for Python 2.6/2.7.
    'wx': is_py2,
}


def main():
    parser = optparse.OptionParser()
    parser.add_option('-d', '--download-dir',
        help='Directory with maually downloaded python modules.'
    )
    opts, _ = parser.parse_args()

    # Install packages.
    for k, v in _PACKAGES.items():
        # Test python version for module.
        if k in _PY_VERSION:
            # Python version too old, skip module.
            if PYVER < _PY_VERSION[k]:
                continue
        try:
            __import__(k)
            print('Already installed...', k)
        # Module is not available - install it.
        except ImportError:
            # If not url or module name then look for installers in download area.
            if not v[0].startswith('http') and v[0].endswith('exe'):
                files = []
                # Try all file patterns.
                for pattern in v:
                    pattern = os.path.join(opts.download_dir, pattern)
                    files += glob.glob(pattern)
                # No file with that pattern was not found - skip it.
                if not files:
                    print('Skipping module...', k)
                    continue
                # Full path to installers in download directory.
                v = files
            print('Installing module...', k)
            # Some modules might require several .exe files to install.
            for f in v:
                print(' ', f)
                # Use --no-deps ... installing module dependencies might fail
                # because easy_install tries to install the same module from
                # PYPI from source code and if fails because of C code that
                # that needs to be compiled.
                try:
                    easy_install.main(['--no-deps', '--always-unzip', f])
                except Exception:
                    print(' ', k, 'installation failed')


if __name__ == '__main__':
    main()
