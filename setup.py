#! /usr/bin/env python
#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import os
import stat
from setuptools import setup, find_packages
from distutils.command.build_py import build_py
from distutils.command.sdist import sdist

from PyInstaller import get_version
import PyInstaller.utils.git


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
Classifier: Development Status :: 5 - Production/Stable
Classifier: Environment :: Console
Classifier: Intended Audience :: Developers
Classifier: Intended Audience :: Other Audience
Classifier: Intended Audience :: System Administrators
Classifier: License :: OSI Approved :: GNU General Public License v2 (GPLv2)
Classifier: Natural Language :: English
Classifier: Operating System :: MacOS :: MacOS X
Classifier: Operating System :: Microsoft :: Windows
Classifier: Operating System :: POSIX
Classifier: Operating System :: POSIX :: AIX
Classifier: Operating System :: POSIX :: Linux
Classifier: Operating System :: POSIX :: SunOS/Solaris
Classifier: Programming Language :: C
Classifier: Programming Language :: Python
Classifier: Programming Language :: Python :: 2
Classifier: Programming Language :: Python :: 2.4
Classifier: Programming Language :: Python :: 2.5
Classifier: Programming Language :: Python :: 2.6
Classifier: Programming Language :: Python :: 2.7
Classifier: Programming Language :: Python :: 2 :: Only
Classifier: Programming Language :: Python :: Implementation :: CPython
Classifier: Topic :: Software Development
Classifier: Topic :: Software Development :: Build Tools
Classifier: Topic :: System :: Installation/Setup
Classifier: Topic :: System :: Software Distribution
Classifier: Topic :: Utilities
""".splitlines()

# Make the distribution files to always report the git-revision used
# then building the distribution packages. This is done by replacing
# PyInstaller/utils/git.py within the dist/build by a fake-module
# which always returns the current git-revision. The original
# source-file is unchanged.
#
# This has to be done in 'build_py' for bdist-commands and in 'sdist'
# for sdist-commands.

def _write_git_version_file(filename):
    """
    Fake PyInstaller.utils.git.py to always return the current revision.
    """
    git_version = PyInstaller.utils.git.get_repo_revision()
    st = os.stat(filename)
    # remove the file first for the case it's hard-linked to the
    # original file
    os.remove(filename)
    git_mod = open(filename, 'w')
    template = "def get_repo_revision(): return %r"
    try:
        git_mod.write(template % git_version)
    finally:
        git_mod.close()
    os.chmod(filename, stat.S_IMODE(st.st_mode))


class my_build_py(build_py):
    def build_module(self, module, module_file, package):
        res = build_py.build_module(self, module, module_file, package)
        if module == 'git' and package == 'PyInstaller.utils':
            filename = self.get_module_outfile(
                self.build_lib, package.split('.'), module)
            _write_git_version_file(filename)
        return res


class my_sdist(sdist):
    def make_release_tree(self, base_dir, files):
        res = sdist.make_release_tree(self, base_dir, files)
        build_py = self.get_finalized_command('build_py')
        filename = build_py.get_module_outfile(
            base_dir, ['PyInstaller', 'utils'], 'git')
        _write_git_version_file(filename)
        return res

setup(
    install_requires=['setuptools'],

    name='PyInstaller',
    version=get_version(),

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
    packages=find_packages(),
    package_data={
        # This includes precompiled bootloaders.
        'PyInstaller': ['bootloader/*/*'],
        # This file is necessary for rthooks (runtime hooks).
        'PyInstaller.loader': ['rthooks.dat'],
        },
    include_package_data=True,
    cmdclass = {
        'sdist': my_sdist,
        'build_py': my_build_py,
        },

    entry_points="""
    [console_scripts]
    pyinstaller=PyInstaller.main:run
    pyi-archive_viewer=PyInstaller.cliutils.archive_viewer:run
    pyi-bindepend=PyInstaller.cliutils.bindepend:run
    pyi-build=PyInstaller.cliutils.build:run
    pyi-grab_version=PyInstaller.cliutils.grab_version:run
    pyi-make_comserver=PyInstaller.cliutils.make_comserver:run
    pyi-makespec=PyInstaller.cliutils.makespec:run
    pyi-pprint_toc=PyInstaller.cliutils.pprint_toc:run
    pyi-set_version=PyInstaller.cliutils.set_version:run
    """
)
