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
# Python there is mostly 64bit. Only Python 2.4 is 32bit on Windows 7.


import glob
import optparse
import os
import platform
import sys

# easy_install command used in a Python script.
from setuptools.command import easy_install


try:
    import PyInstaller
except ImportError:
    # if importing PyInstaller fails, try to load from parent
    # directory to support running without installation
    import imp
    if not hasattr(os, "getuid") or os.getuid() != 0:
        imp.load_module('PyInstaller', *imp.find_module('PyInstaller',
            [os.path.dirname(os.path.dirname(os.path.abspath(__file__)))]))


from PyInstaller.compat import is_py25, is_py26


PYVER = '.'.join([str(x) for x in sys.version_info[0:2]])


def py_arch():
    """
    .exe installers of Python modules contain architecture name in filename.
    """
    mapping = {'32bit': 'win32', '64bit': 'win-amd64'}
    arch = platform.architecture()[0]
    return mapping[arch]


_PACKAGES = {
    'docutils': ['docutils'],
    'jinja2': ['jinja2'],
    'sphinx': ['sphinx'],
    'pytz': ['pytz'],
    # 'modulename': 'pypi_name_or_url_or_path'
    'MySQLdb': ['MySQL-python-*%s-py%s.exe' % (py_arch(), PYVER)],
    'numpy': ['numpy-unoptimized-*%s-py%s.exe' % (py_arch(), PYVER)],
    'PIL': ['PIL-*%s-py%s.exe' % (py_arch(), PYVER)],
    'psycopg2': ['psycopg2-*%s-py%s.exe' % (py_arch(), PYVER)],
    #'pycrypto': ['pycrypto'],
    'pyodbc': ['pyodbc'],
    #'simplejson': ['simplejson'],
    'sqlalchemy': ['SQLAlchemy-*%s-py%s.exe' % (py_arch(), PYVER)],
    'wx': ['wxPython-common-*%s-py%s.exe' % (py_arch(), PYVER),
        'wxPython-2*%s-py%s.exe' % (py_arch(), PYVER)],
    'win32api': ['http://downloads.sourceforge.net/project/pywin32/pywin32/Build%%20217/pywin32-217.%s-py%s.exe' %
        (py_arch(), PYVER)],
}

_PY_VERSION = {
    'MySQLdb': is_py26,
    'numpy': is_py26,
    'PIL': is_py26,
    'psycopg2': is_py26,
    'simplejson': is_py25,
    # Installers are available only for Python 2.6/2.7.
    'wx': is_py26,
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
            print 'Already installed... %s' % k
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
                    print 'Skipping module... %s' % k
                    continue
                # Full path to installers in download directory.
                v = files
            print 'Installing module... %s' % k
            # Some modules might require several .exe files to install.
            for f in v:
                print '  %s' % f
                # Use --no-deps ... installing module dependencies might fail
                # because easy_install tries to install the same module from
                # PYPI from source code and if fails because of C code that
                # that needs to be compiled.
                try:
                    easy_install.main(['--no-deps', '--always-unzip', f])
                except Exception:
                    print '  %s installation failed' % k


if __name__ == '__main__':
    main()
