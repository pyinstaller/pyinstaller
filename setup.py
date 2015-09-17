#! /usr/bin/env python
#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import sys
from setuptools import setup
from PyInstaller import __version__ as version


REQUIREMENTS = ['setuptools']
if sys.platform.startswith('win'):
    # 'pypiwin32' is PyWin32 package made installable by 'pip install'
    # command.
    REQUIREMENTS.append('pypiwin32')


DESC = ('Converts (packages) Python programs into stand-alone executables, '
        'under Windows, Linux, Mac OS X, AIX and Solaris.')

LONG_DESC = """
PyInstaller is a program that converts (packages) Python
programs into stand-alone executables, under Windows, Linux, Mac OS X,
AIX and Solaris. Its main advantages over similar tools are that
PyInstaller works with any version of Python since 2.3, it builds smaller
executables thanks to transparent compression, it is fully multi-platform,
and uses the OS support to load the dynamic libraries, thus ensuring full
compatibility.

The main goal of PyInstaller is to be compatible with 3rd-party packages
out-of-the-box. This means that, with PyInstaller, all the required tricks
to make external packages work are already integrated within PyInstaller
itself so that there is no user intervention required. You'll never be
required to look for tricks in wikis and apply custom modification to your
files or your setup scripts. As an example, libraries like PyQt, Django or
matplotlib are fully supported, without having to handle plugins or
external data files manually.
"""


CLASSIFIERS = """
Development Status :: 5 - Production/Stable
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

    description=DESC,
    long_description=LONG_DESC,
    keywords='packaging, standalone executable, pyinstaller, macholib, freeze, py2exe, py2app, bbfreeze',

    author='Giovanni Bajo, Hartmut Goebel, Martin Zibricky',
    author_email='pyinstaller@googlegroups.com',
    maintainer='Giovanni Bajo, Hartmut Goebel, Martin Zibricky',
    maintainer_email='pyinstaller@googlegroups.com',

    license=('GPL license with a special exception which allows to use '
             'PyInstaller to build and distribute non-free programs '
             '(including commercial ones)'),
    url='http://www.pyinstaller.org',
    download_url='https://sourceforge.net/projects/pyinstaller/files',

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

    entry_points="""
    [console_scripts]
    pyinstaller=PyInstaller.__main__:run
    pyi-archive_viewer=PyInstaller.utils.cliutils.archive_viewer:run
    pyi-bindepend=PyInstaller.utils.cliutils.bindepend:run
    pyi-build=PyInstaller.utils.cliutils.build:run
    pyi-grab_version=PyInstaller.utils.cliutils.grab_version:run
    pyi-make_comserver=PyInstaller.utils.cliutils.make_comserver:run
    pyi-makespec=PyInstaller.utils.cliutils.makespec:run
    pyi-pprint_toc=PyInstaller.utils.cliutils.pprint_toc:run
    pyi-set_version=PyInstaller.utils.cliutils.set_version:run
    """
)
