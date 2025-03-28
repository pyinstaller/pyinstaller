#-----------------------------------------------------------------------------
# Copyright (c) 2005-2023, PyInstaller Development Team.
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
from setuptools.command.bdist_wheel import bdist_wheel

#-- plug-in building the bootloader

from distutils.core import Command
from distutils.command.build import build

# Hack that prevents PyInstaller.compat from failing due to unmet run-time dependencies (importlib-metadata on
# python < 3.10, pywin32-ctypes on Windows). These dependencies are not required for the subset of functionality that is
# used here in the `setup.py`.
os.environ["_PYINSTALLER_SETUP_PY"] = "1"


class build_bootloader(Command):
    """
    Wrapper for distutil command `build`.
    """

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def bootloader_exists(self):
        # Checks if the console, non-debug bootloader exists
        from PyInstaller import HOMEPATH, PLATFORM
        exe = 'run'
        pyi_platform = os.environ.get("PYI_PLATFORM", PLATFORM)
        if "Windows" in pyi_platform:
            exe = 'run.exe'
        exe = os.path.join(HOMEPATH, 'PyInstaller', 'bootloader', pyi_platform, exe)
        return os.path.isfile(exe)

    def compile_bootloader(self):
        import subprocess
        from PyInstaller import HOMEPATH

        src_dir = os.path.join(HOMEPATH, 'bootloader')
        additional_args = os.getenv('PYINSTALLER_BOOTLOADER_WAF_ARGS', '').strip().split()
        cmd = [sys.executable, './waf', 'configure', 'all']
        cmd += additional_args
        rc = subprocess.call(cmd, cwd=src_dir)
        if rc:
            raise SystemExit('ERROR: Failed compiling the bootloader. Please compile manually and rerun')

    def run(self):
        if getattr(self, 'dry_run', False):
            return
        if self.bootloader_exists() and not os.environ.get("PYINSTALLER_COMPILE_BOOTLOADER"):
            return
        print(
            'No precompiled bootloader found or compile forced. Trying to compile the bootloader for you ...',
            file=sys.stderr
        )
        self.compile_bootloader()
        if not self.bootloader_exists():
            raise SystemExit("ERROR: Bootloaders have been compiled for the wrong platform")


class MyBuild(build):
    # plug `build_bootloader` into the `build` command
    def run(self):
        self.run_command('build_bootloader')
        build.run(self)


# --- Builder class for separate per-platform wheels. ---


class Wheel(bdist_wheel):
    """
    Base class for building a wheel for one platform, collecting only the relevant bootloaders for that platform.
    """
    def finalize_options(self):
        # Inject the platform name.
        if os.environ.get("PYI_WHEEL_TAG"):
            self.plat_name = os.environ["PYI_WHEEL_TAG"]
            self.plat_name_supplied = True
        self.pyi_platform = os.environ.get("PYI_PLATFORM")

        if self.pyi_platform:
            if "Darwin" in self.pyi_platform:
                icons = ["icns"]
            elif "Windows" in self.pyi_platform:
                icons = ["ico"]
            else:
                icons = []
        else:
            icons = ["ico", "icns"]

        self.distribution.package_data = {
            "PyInstaller": [
                # And add the correct bootloaders as data files.
                f"bootloader/{self.pyi_platform or '*'}/*",
                *(f"bootloader/images/*.{suffix}" for suffix in icons),
                # These files need to be explicitly included as well.
                "fake-modules/*.py",
                "fake-modules/_pyi_rth_utils/*.py",
                "hooks/rthooks.dat",
                "lib/README.rst",
            ],
        }
        super().finalize_options()

    def run(self):
        # Note that 'clean' relies on clean::all=1 being set in the `setup.cfg` or the build cache "leaks" into
        # subsequently built wheels.
        self.run_command("clean")
        super().run()


#--

# --- Prevent `python setup.py install` from building and installing eggs ---

if "bdist_egg" not in sys.argv:
    from setuptools.command.bdist_egg import bdist_egg

    class bdist_egg_disabled(bdist_egg):
        """
        Disabled version of bdist_egg, which prevents `setup.py install` from performing setuptools' default
        easy_install, which is deprecated and should be avoided.
        """
        def run(self):
            raise SystemExit(
                "Error: Aborting implicit building of eggs. To install from source, use `pip install .` instead of "
                "`python setup.py install`."
            )

    bdist_egg_override = {'bdist_egg': bdist_egg_disabled}
else:
    bdist_egg_override = {}

#--

setup(
    setup_requires=["setuptools >= 42.0.0"],
    cmdclass={
        'build_bootloader': build_bootloader,
        'build': MyBuild,
        'bdist_wheel': Wheel,
        **bdist_egg_override,
    },
)
