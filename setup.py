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
import subprocess
from typing import Type

from setuptools import setup

#-- plug-in building the bootloader

from distutils.core import Command
from distutils.command.build import build

# Hack that prevents PyInstaller.compat from failing due to unmet run-time dependencies (importlib-metadata on
# python < 3.10, pywin32-ctypes on Windows). These dependencies are not required for the subset of functionality that is
# used here in the `setup.py`.
os.environ["_PYINSTALLER_SETUP_PY"] = "1"

try:
    from wheel.bdist_wheel import bdist_wheel
except ImportError:
    raise SystemExit("Error: Building wheels requires the 'wheel' package. Please `pip install wheel` then try again.")


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
        additional_args = os.getenv('PYINSTALLER_BOOTLOADER_WAF_ARGS', '').strip().split()
        cmd = [sys.executable, './waf', 'configure', 'all']
        cmd += additional_args
        rc = subprocess.call(cmd, cwd=src_dir)
        if rc:
            raise SystemExit('ERROR: Failed compiling the bootloader. Please compile manually and rerun setup.py')

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


class MyBuild(build):
    # plug `build_bootloader` into the `build` command
    def run(self):
        self.run_command('build_bootloader')
        build.run(self)


# --- Builder classes for separate per-platform wheels. ---


class Wheel(bdist_wheel):
    """
    Base class for building a wheel for one platform, collecting only the relevant bootloaders for that platform.
    """

    # The setuptools platform tag.
    PLAT_NAME = "manylinux2014_x86_64"
    # The folder of bootloaders from PyInstaller/bootloaders to include.
    PYI_PLAT_NAME = "Linux-64bit-intel"
    ICON_TYPES = []

    def finalize_options(self):
        # Inject the platform name.
        self.plat_name = self.PLAT_NAME
        self.plat_name_supplied = True

        if not self.has_bootloaders():
            raise SystemExit(
                f"Error: No bootloaders for {self.PLAT_NAME} found in {self.bootloaders_dir()}. See "
                f"https://pyinstaller.readthedocs.io/en/stable/bootloader-building.html for how to compile them."
            )

        self.distribution.package_data = {
            "PyInstaller": [
                # And add the correct bootloaders as data files.
                f"bootloader/{self.PYI_PLAT_NAME}/*",
                *(f"bootloader/images/*.{suffix}" for suffix in self.ICON_TYPES),
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

    @classmethod
    def bootloaders_dir(cls):
        """
        Locate the bootloader folder inside the PyInstaller package.
        """
        return f"PyInstaller/bootloader/{cls.PYI_PLAT_NAME}"

    @classmethod
    def has_bootloaders(cls):
        """
        Does the bootloader folder exist and is there anything in it?
        """
        dir = cls.bootloaders_dir()
        return os.path.exists(dir) and len(os.listdir(dir))


# Map PyInstaller platform names to their setuptools counterparts. Other OSs can be added as and when we start shipping
# wheels for them.
PLATFORMS = {
    "Windows-64bit-intel": "win_amd64",
    "Windows-32bit-intel": "win32",
    "Windows-64bit-arm": "win_arm64",
    # The manylinux version tag depends on the glibc version compiled against. If we ever change the docker image used
    # to build the bootloaders, we must check/update this tag. These are the only architectures currently supported
    # by manylinux. Other platforms must use the generic bdist_wheel command, which will produce a wheel that is not
    # allowed on PyPI.
    "Linux-64bit-intel": "manylinux2014_x86_64",
    "Linux-32bit-intel": "manylinux2014_i686",
    "Linux-64bit-arm": "manylinux2014_aarch64",
    "Linux-64bit-ppc": "manylinux2014_ppc64le",
    "Linux-64bit-s390x": "manylinux2014_s390x",
    "Linux-64bit-intel-musl": "musllinux_1_1_x86_64",
    "Linux-64bit-arm-musl": "musllinux_1_1_aarch64",
    # macOS needs special handling. This gets done dynamically later.
    "Darwin-64bit": None,
}

# Create a subclass of Wheel() for each platform.
wheel_commands = {}
for (pyi_plat_name, plat_name) in PLATFORMS.items():
    # This is the name it will have on the setup.py command line.
    command_name = "wheel_" + pyi_plat_name.replace("-", "_").lower()

    # Create and register the subclass, overriding the PLAT_NAME and PYI_PLAT_NAME attributes.
    platform = {"PLAT_NAME": plat_name, "PYI_PLAT_NAME": pyi_plat_name}
    command: Type[Wheel] = type(command_name, (Wheel,), platform)
    command.description = f"Create a {command.PYI_PLAT_NAME} wheel"
    wheel_commands[command_name] = command


class bdist_macos(wheel_commands["wheel_darwin_64bit"]):
    def finalize_options(self):
        """
        Choose a platform tag that reflects the platform of the bootloaders.

        Namely:
        * The minimum supported macOS version should mirror that of the bootloaders.
        * The architecture should similarly mirror the bootloader architecture(s).
        """
        try:
            from PyInstaller.utils.osx import get_binary_architectures, macosx_version_min
        except ImportError:
            raise SystemExit(
                "Building wheels for macOS requires that PyInstaller and macholib be installed. Please run:\n"
                "    pip install -e . macholib"
            )

        bootloader = os.path.join(self.bootloaders_dir(), "run")
        is_fat, architectures = get_binary_architectures(bootloader)

        if is_fat and sorted(architectures) == ["arm64", "x86_64"]:
            # An arm64 + x86_64 dual architecture binary gets the special name universal2.
            architectures = "universal2"
        else:
            # It is unlikely that there will be other multi-architecture types, but if one crops up, the syntax is to
            # join them with underscores.
            architectures = "_".join(architectures)

        # Fetch the macOS deployment target the bootloaders are compiled with and set that in the tag too.
        version = "_".join(map(str, macosx_version_min(bootloader)[:2]))

        self.PLAT_NAME = f"macosx_{version}_{architectures}"
        super().finalize_options()


wheel_commands["wheel_darwin_64bit"] = bdist_macos

wheel_commands["wheel_darwin_64bit"].ICON_TYPES = ["icns"]
for name in ["wheel_windows_64bit_intel", "wheel_windows_32bit_intel", "wheel_windows_64bit_arm"]:
    wheel_commands[name].ICON_TYPES = ["ico"]


class bdist_wheels(Command):
    """
    Build a wheel for every platform listed in the PLATFORMS dict, which has bootloaders available in
    `PyInstaller/bootloaders/[platform-name]`.
    """
    description = "Build all available wheel types"

    # Overload these to keep the abstract metaclass happy.
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self) -> None:
        command: Type[Wheel]
        for (name, command) in wheel_commands.items():
            if not command.has_bootloaders():
                print("Skipping", name, "because no bootloaders were found in", command.bootloaders_dir())
                continue

            print("running", name)
            # This should be `self.run_command(name)`, but there is some aggressive caching from distutils, which has
            # to be suppressed by us using forced cleaning. One distutils behaviour that seemingly cannot be disabled
            # is that each command should only run once - this is at odds with what we want, because we need to run
            # 'build' for every platform. The only way I can get it not to skip subsequent builds is to isolate the
            # processes completely using subprocesses...
            subprocess.run([sys.executable, __file__, "-q", name], stderr=subprocess.PIPE, check=True)


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
        **wheel_commands,
        'bdist_wheels': bdist_wheels,
        **bdist_egg_override,
    },
)
