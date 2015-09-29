#! /usr/bin/env python
#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import codecs
import sys
from setuptools import setup
from PyInstaller import __version__ as version



REQUIREMENTS = ['setuptools']
# For Windows install PyWin32 if not already installed.
if sys.platform.startswith('win'):
    try:
        import pywintypes
    except ImportError:
        # 'pypiwin32' is PyWin32 package made installable by 'pip install'
        # command.
        REQUIREMENTS.append('pypiwin32')


# Create long description from README.rst and doc/CHANGES.rst.
# PYPI page will contain complete PyInstaller changelog.
def read(filename):
    try:
        return unicode(codecs.open(filename, encoding='utf-8').read())
    except NameError:
        return open(filename, 'r', encoding='utf-8').read()
long_description = u'\n\n'.join([read('README.rst'),
                                 read('doc/CHANGES.rst')])
if sys.version_info < (3,):
    long_description = long_description.encode('utf-8')


CLASSIFIERS = """
Development Status :: 6 - Mature
Environment :: Console
Intended Audience :: Developers
Intended Audience :: Other Audience
Intended Audience :: System Administrators
License :: OSI Approved :: GNU General Public License v2 (GPLv2)
Natural Language :: English
Operating System :: MacOS :: MacOS X
Operating System :: Microsoft :: Windows
Operating System :: POSIX
Operating System :: POSIX :: AIX
Operating System :: POSIX :: BSD
Operating System :: POSIX :: Linux
Operating System :: POSIX :: SunOS/Solaris
Programming Language :: C
Programming Language :: Python
Programming Language :: Python :: 2
Programming Language :: Python :: 2.7
Programming Language :: Python :: 3
Programming Language :: Python :: 3.3
Programming Language :: Python :: 3.4
Programming Language :: Python :: 3.5
Programming Language :: Python :: Implementation :: CPython
Topic :: Software Development
Topic :: Software Development :: Build Tools
Topic :: Software Development :: Interpreters
Topic :: Software Development :: Libraries :: Python Modules
Topic :: System :: Installation/Setup
Topic :: System :: Software Distribution
Topic :: Utilities
""".strip().splitlines()


setup(
    install_requires=REQUIREMENTS,

    name='PyInstaller',
    version=version,

    description='PyInstaller bundles a Python application and all its '
                'dependencies into a single package.',
    long_description=long_description,
    keywords='packaging app apps bundle convert standalone executable '
             'pyinstaller macholib cxfreeze freeze py2exe py2app bbfreeze',

    author='Giovanni Bajo, Hartmut Goebel, David Vierra, David Cortesi, Martin Zibricky',
    author_email='pyinstaller@googlegroups.com',

    license=('GPL license with a special exception which allows to use '
             'PyInstaller to build and distribute non-free programs '
             '(including commercial ones)'),
    url='http://www.pyinstaller.org',

    classifiers=CLASSIFIERS,
    zip_safe=False,
    packages=['PyInstaller'],
    package_data={
        # This includes precompiled bootloaders and icons for bootloaders.
        'PyInstaller': ['bootloader/*/*'],
        # This file is necessary for rthooks (runtime hooks).
        'PyInstaller.loader': ['rthooks.dat'],
        },
    include_package_data=True,

    entry_points={
        'console_scripts': [
            'pyinstaller = PyInstaller.__main__:run',
            'pyi-archive_viewer = PyInstaller.utils.cliutils.archive_viewer:run',
            'pyi-bindepend = PyInstaller.utils.cliutils.bindepend:run',
            'pyi-grab_version = PyInstaller.utils.cliutils.grab_version:run',
            'pyi-makespec = PyInstaller.utils.cliutils.makespec:run',
            'pyi-pprint_toc = PyInstaller.utils.cliutils.pprint_toc:run',
            'pyi-set_version = PyInstaller.utils.cliutils.set_version:run',
        ],
    }
)
