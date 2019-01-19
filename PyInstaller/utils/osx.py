#-----------------------------------------------------------------------------
# Copyright (c) 2014-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Utils for Mac OS X platform.
"""

import os

from ..compat import base_prefix, exec_command, exec_command_rc
from macholib.MachO import MachO


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
    prefix = exec_command(['/bin/bash', '-c', 'which brew']).strip()
    # Conversion:  /usr/local/bin/brew -> /usr/local
    prefix = os.path.dirname(os.path.dirname(prefix))
    return prefix


def get_macports_prefix():
    """
    :return: Root path of the Macports environment.
    """
    prefix = exec_command(['/bin/bash', '-c', 'which port']).strip()
    # Conversion:  /usr/local/bin/brew -> /usr/local
    prefix = os.path.dirname(os.path.dirname(prefix))
    return prefix


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


def code_sign(binary, identity, deep=None, verbose=True):
    """ Code sign binary (.so, .dylib, or .app) using identity.

    Relies on the codesign utility which must be in PATH.

    binary
        (str) Full path to the binary or .app to be signed.
    identity
        (str) The code signing identity to use (as you would give to the
              ``codesign -s`` option on the command-line).
    deep
        (bool) Specify whether to use the codesign --deep option. If not
               specified, will auto-detect based on whether ``binary`` is a
               directory (such as a .app or .framework) or a stand-alone file.
    verbose
        (bool) Specify whether codesign output should be verbose.
    """
    if deep is None and os.path.isdir(binary):
        deep = True
    deep = '--deep' if deep else ''
    verbose = '-v' if verbose else ''

    binary_dir = os.path.dirname(binary)
    saved_cwd = None
    try:
        if binary_dir:
            # switch to directory of the binary so codesign verbose messages
            # don't include long path
            _saved = os.getcwd()
            os.chdir(binary_dir)
            saved_cwd = _saved  # chdir success, save for `finally:` below
            binary = os.path.basename(binary)
        args = ["codesign", "-f", "-s", identity, binary]
        fargpos = 1
        if verbose:
            args.insert(fargpos, verbose)
            fargpos += 1
        if deep:
            args.insert(fargpos + 1, deep)

        err_msg, result = '', None
        try:
            result = exec_command_rc(*args)
        except OSError as e:
            err_msg = " (Error was: " + repr(e) + ")"
        if 0 != result:
            raise SystemExit('Error: Failed to code sign binary {} using '
                             'identity "{}". Please ensure that the '
                             '``codesign`` utility is in your PATH and that '
                             'the identity specified is valid for signing.{}'
                             .format(binary, identity, err_msg))
    finally:
        if saved_cwd:
            os.chdir(saved_cwd)
