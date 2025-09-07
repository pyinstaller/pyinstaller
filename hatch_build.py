#-----------------------------------------------------------------------------
# Copyright (c) 2025, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import os
import sys

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

sys.path.insert(0, os.path.dirname(__file__))

# Hack that prevents PyInstaller.compat from failing due to unmet run-time dependencies (importlib-metadata on
# python < 3.10, pywin32-ctypes on Windows). These dependencies are not required for the subset of functionality that is
# used here.
os.environ["_PYINSTALLER_SETUP"] = "1"


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        # Inject the platform specifier into the wheel's filename.
        if os.environ.get("PYI_WHEEL_TAG"):
            build_data["tag"] = "py3-none-" + os.environ["PYI_WHEEL_TAG"]

        pyi_platform = os.environ.get("PYI_PLATFORM")
        if pyi_platform:
            if "Darwin" in pyi_platform:
                icons = ["icns"]
            elif "Windows" in pyi_platform:
                icons = ["ico"]
            else:
                icons = []
        else:
            icons = ["ico", "icns"]

        build_data["artifacts"] += [
            f"PyInstaller/bootloader/{pyi_platform or '*'}/*",
            *(f"PyInstaller/bootloader/images/*.{suffix}" for suffix in icons),
        ]
        self.run()

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
        if self.bootloader_exists() and not os.environ.get("PYINSTALLER_COMPILE_BOOTLOADER"):
            return
        print(
            'No precompiled bootloader found or compile forced. Trying to compile the bootloader for you ...',
            file=sys.stderr
        )
        self.compile_bootloader()
        if not self.bootloader_exists():
            raise SystemExit("ERROR: Bootloaders have been compiled for the wrong platform")
