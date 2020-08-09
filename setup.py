#! /usr/bin/env python
#-----------------------------------------------------------------------------
# Copyright (c) 2005-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import sys
import os
from setuptools import setup

# Hack required to allow compat to not fail when pypiwin32 isn't found
os.environ["PYINSTALLER_NO_PYWIN32_FAILURE"] = "1"


#-- plug-in building the bootloader

from distutils.core import Command
from distutils.command.build import build


class build_bootloader(Command):
    """
    Wrapper for distutil command `build`.
    """

    user_options =[]
    def initialize_options(self): pass
    def finalize_options(self): pass

    def bootloader_exists(self):
        # Checks is the console, non-debug bootloader exists
        from PyInstaller import HOMEPATH, PLATFORM
        from PyInstaller.compat import is_win, is_cygwin
        exe = 'run'
        if is_win or is_cygwin:
            exe = 'run.exe'
        exe = os.path.join(HOMEPATH, 'PyInstaller', 'bootloader', PLATFORM, exe)
        return os.path.isfile(exe)

    def compile_bootloader(self):
        import subprocess
        from PyInstaller import HOMEPATH

        src_dir = os.path.join(HOMEPATH, 'bootloader')
        cmd = [sys.executable, './waf', 'configure', 'all']
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

#--

setup(
    setup_requires = ["setuptools >= 39.2.0"],
    cmdclass = {'build_bootloader': build_bootloader,
                'build': MyBuild,
                },
)
