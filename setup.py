#! /usr/bin/env python
#-----------------------------------------------------------------------------
# Copyright (c) 2005-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from __future__ import print_function

import codecs
import sys, os
from setuptools import setup
from PyInstaller import (__version__ as version, is_linux, is_win, is_cygwin,
                         HOMEPATH, PLATFORM, compat)



REQUIREMENTS = ['setuptools']
# For Windows install PyWin32 if not already installed.
if sys.platform.startswith('win'):
    # Windows support depends on pefile library.
    REQUIREMENTS.append('pefile')
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


#-- plug-in building the bootloader

from distutils.core import Command
from distutils.command.build import build
from setuptools.command.bdist_egg import bdist_egg


class build_bootloader(Command):
    """
    Wrapper for distutil command `build`.
    """

    user_options =[]
    def initialize_options(self): pass
    def finalize_options(self): pass

    def bootloader_exists(self):
        # Checks is the console, non-debug bootloader exists
        exe = 'run'
        if is_win or is_cygwin:
            exe = 'run.exe'
        exe = os.path.join(HOMEPATH, 'PyInstaller', 'bootloader', PLATFORM, exe)
        return os.path.isfile(exe)

    def compile_bootloader(self):
        import subprocess

        src_dir = os.path.join(HOMEPATH, 'bootloader')
        cmd = [sys.executable, './waf', 'configure', 'all']
        nolsb = True
        if is_linux:
            env = os.environ.copy()
            try:
                env['PATH'] += ':/opt/lsb/bin'
            except:
                env['PATH'] = '/opt/lsb/bin'
            try:
                FNULL = open(os.devnull, 'w')
                if subprocess.call(['which', 'lsbcc'], env=env,
                                   stderr=FNULL, stdout=FNULL,
                                   close_fds=True) == 0:
                    nolsb = False
            except compat.FileNotFoundError:
                pass
        if nolsb:
            cmd.append('--no-lsb')
        rc = subprocess.call(cmd, cwd=src_dir)
        if rc:
            raise SystemExit('ERROR: Failed compiling the bootloader. '
                             'Please compile manually and rerun setup.py')

    def run(self):
        if getattr(self, 'dry_run', False):
            return
        if self.bootloader_exists():
            return
        print('No precompiled bootloader found. Trying to compile it for you ...',
              file=sys.stderr)
        self.compile_bootloader()


class MyBuild(build):
    # plug `build_bootloader` into the `build` command
    def run(self):
        self.run_command('build_bootloader')
        build.run(self)

class MyBDist_Egg(bdist_egg):
    def run(self):
        self.run_command('build_bootloader')
        bdist_egg.run(self)

#--

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

    cmdclass = {'build_bootloader': build_bootloader,
                'build': MyBuild,
                'bdist_egg': MyBDist_Egg,
                },

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
            'pyi-set_version = PyInstaller.utils.cliutils.set_version:run',
        ],
    }
)
