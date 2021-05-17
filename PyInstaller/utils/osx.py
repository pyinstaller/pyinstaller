#-----------------------------------------------------------------------------
# Copyright (c) 2014-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------


"""
Utils for Mac OS X platform.
"""

import os
import shutil

from PyInstaller.compat import base_prefix
from macholib.MachO import MachO
from macholib.mach_o import LC_BUILD_VERSION, LC_VERSION_MIN_MACOSX


def is_homebrew_env():
    """
    Check if Python interpreter was installed via Homebrew command 'brew'.

    :return: True if Homebrew else otherwise.
    """
    # Python path prefix should start with Homebrew prefix.
    env_prefix = get_homebrew_prefix()
    if env_prefix and base_prefix.startswith(env_prefix):
        return True
    return False


def is_macports_env():
    """
    Check if Python interpreter was installed via Macports command 'port'.

    :return: True if Macports else otherwise.
    """
    # Python path prefix should start with Macports prefix.
    env_prefix = get_macports_prefix()
    if env_prefix and base_prefix.startswith(env_prefix):
        return True
    return False


def get_homebrew_prefix():
    """
    :return: Root path of the Homebrew environment.
    """
    prefix = shutil.which('brew')
    # Conversion:  /usr/local/bin/brew -> /usr/local
    prefix = os.path.dirname(os.path.dirname(prefix))
    return prefix


def get_macports_prefix():
    """
    :return: Root path of the Macports environment.
    """
    prefix = shutil.which('port')
    # Conversion:  /usr/local/bin/port -> /usr/local
    prefix = os.path.dirname(os.path.dirname(prefix))
    return prefix


def _find_version_cmd(header):
    """
    Helper that finds the version command in the given MachO header.
    """
    # The SDK version is stored in LC_BUILD_VERSION command (used when
    # targeting the latest versions of macOS) or in older LC_VERSION_MIN_MACOSX
    # command. Check for presence of either.
    version_cmd = [cmd for cmd in header.commands
                   if cmd[0].cmd in {LC_BUILD_VERSION, LC_VERSION_MIN_MACOSX}]
    assert len(version_cmd) == 1, \
        "Expected exactly one LC_BUILD_VERSION or " \
        "LC_VERSION_MIN_MACOSX command!"
    return version_cmd[0]


def get_macos_sdk_version(filename):
    """
    Obtain the version of macOS SDK against which the given binary
    was built.

    NOTE: currently, version is retrieved only from the first arch
    slice in the binary.

    :return: (major, minor, revision) tuple
    """
    binary = MachO(filename)
    header = binary.headers[0]
    # Find version command using helper
    version_cmd = _find_version_cmd(header)
    # Parse SDK version number
    major = (version_cmd[1].sdk & 0xFF0000) >> 16
    minor = (version_cmd[1].sdk & 0xFF00) >> 8
    revision = (version_cmd[1].sdk & 0xFF)
    return major, minor, revision


def set_macos_sdk_version(filename, major, minor, revision):
    """
    Overwrite the macOS SDK version declared in the given binary with
    the specified version.

    NOTE: currently, only version in the first arch slice is modified.
    """
    # Validate values
    assert major >= 0 and major <= 255, "Invalid major version value!"
    assert minor >= 0 and minor <= 255, "Invalid minor version value!"
    assert revision >= 0 and revision <= 255, "Invalid revision value!"
    # Open binary
    binary = MachO(filename)
    header = binary.headers[0]
    # Find version command using helper
    version_cmd = _find_version_cmd(header)
    # Write new SDK version number
    version_cmd[1].sdk = major << 16 | minor << 8 | revision
    # Write changes back.
    with open(binary.filename, 'rb+') as fp:
        binary.write(fp)


def fix_exe_for_code_signing(filename):
    """
    Fixes the Mach-O headers to make code signing possible.

    Code signing on OS X does not work out of the box with embedding
    .pkg archive into the executable.

    The fix is done this way:
    - Make the embedded .pkg archive part of the Mach-O 'String Table'.
      'String Table' is at end of the OS X exe file so just change the size
      of the table to cover the end of the file.
    - Fix the size of the __LINKEDIT segment.

    Mach-O format specification:

    http://developer.apple.com/documentation/Darwin/Reference/ManPages/man5/Mach-O.5.html
    """
    exe_data = MachO(filename)
    # Every load command is a tupple: (cmd_metadata, segment, [section1, section2])
    cmds = exe_data.headers[0].commands  # '0' - Exe contains only one architecture.
    file_size = exe_data.headers[0].size

    ## Make the embedded .pkg archive part of the Mach-O 'String Table'.
    # Data about 'String Table' is in LC_SYMTAB load command.
    for c in cmds:
        if c[0].get_cmd_name() == 'LC_SYMTAB':
            data = c[1]
            # Increase the size of 'String Table' to cover the embedded .pkg file.
            new_strsize = file_size - data.stroff
            data.strsize = new_strsize
    ## Fix the size of the __LINKEDIT segment.
    # __LINKEDIT segment data is the 4th item in the executable.
    linkedit = cmds[3][1]
    new_segsize = file_size - linkedit.fileoff
    linkedit.filesize = new_segsize
    linkedit.vmsize = new_segsize
    ## Write changes back.
    with open(exe_data.filename, 'rb+') as fp:
        exe_data.write(fp)
