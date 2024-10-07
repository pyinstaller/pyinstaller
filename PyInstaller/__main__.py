#-----------------------------------------------------------------------------
# Copyright (c) 2013-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""
Main command-line interface to PyInstaller.
"""
from __future__ import annotations

import argparse
import os
import platform
import sys
import pathlib
from collections import defaultdict

from PyInstaller import __version__
from PyInstaller import log as logging
# Note: do not import anything else until compat.check_requirements function is run!
from PyInstaller import compat

try:
    from argcomplete import autocomplete
except ImportError:

    def autocomplete(parser):
        return None


logger = logging.getLogger(__name__)

# Taken from https://stackoverflow.com/a/22157136 to format args more flexibly: any help text which beings with ``R|``
# will have all newlines preserved; the help text will be line wrapped. See
# https://docs.python.org/3/library/argparse.html#formatter-class.


# This is used by the ``--debug`` option.
class _SmartFormatter(argparse.HelpFormatter):
    def _split_lines(self, text, width):
        if text.startswith('R|'):
            # The underlying implementation of ``RawTextHelpFormatter._split_lines`` invokes this; mimic it.
            return text[2:].splitlines()
        else:
            # Invoke the usual formatter.
            return super()._split_lines(text, width)


def run_makespec(filenames, **opts):
    # Split pathex by using the path separator
    temppaths = opts['pathex'][:]
    pathex = opts['pathex'] = []
    for p in temppaths:
        pathex.extend(p.split(os.pathsep))

    import PyInstaller.building.makespec

    spec_file = PyInstaller.building.makespec.main(filenames, **opts)
    logger.info('wrote %s' % spec_file)
    return spec_file


def run_build(pyi_config, spec_file, **kwargs):
    import PyInstaller.building.build_main
    PyInstaller.building.build_main.main(pyi_config, spec_file, **kwargs)


def __add_options(parser):
    parser.add_argument(
        '-v',
        '--version',
        action='version',
        version=__version__,
        help='Show program version info and exit.',
    )


class _PyiArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        self._pyi_action_groups = defaultdict(list)
        super().__init__(*args, **kwargs)

    def _add_options(self, __add_options: callable, name: str = ""):
        """
        Mutate self with the given callable, storing any new actions added in a named group
        """
        n_actions_before = len(getattr(self, "_actions", []))
        __add_options(self)  # preserves old behavior
        new_actions = getattr(self, "_actions", [])[n_actions_before:]
        self._pyi_action_groups[name].extend(new_actions)

    def _option_name(self, action):
        """
        Get the option name(s) associated with an action

        For options that define both short and long names, this function will
        return the long names joined by "/"
        """
        longnames = [name for name in action.option_strings if name.startswith("--")]
        if longnames:
            name = "/".join(longnames)
        else:
            name = action.option_strings[0]
        return name

    def _forbid_options(self, args: argparse.Namespace, group: str, errmsg: str = ""):
        """Forbid options from a named action group"""
        options = defaultdict(str)
        for action in self._pyi_action_groups[group]:
            dest = action.dest
            name = self._option_name(action)
            if getattr(args, dest) is not self.get_default(dest):
                if dest in options:
                    options[dest] += "/"
                options[dest] += name

        # if any options from the forbidden group are not the default values,
        # the user must have passed them in, so issue an error report
        if options:
            sep = "\n  "
            bad = sep.join(options.values())
            if errmsg:
                errmsg = "\n" + errmsg
            raise SystemExit(f"option(s) not allowed:{sep}{bad}{errmsg}")


def generate_parser() -> _PyiArgumentParser:
    """
    Build an argparse parser for PyInstaller's main CLI.
    """

    import PyInstaller.building.build_main
    import PyInstaller.building.makespec
    import PyInstaller.log

    parser = _PyiArgumentParser(formatter_class=_SmartFormatter)
    parser.prog = "pyinstaller"

    parser._add_options(__add_options)
    parser._add_options(PyInstaller.building.makespec.__add_options, name="makespec")
    parser._add_options(PyInstaller.building.build_main.__add_options, name="build_main")
    parser._add_options(PyInstaller.log.__add_options, name="log")

    parser.add_argument(
        'filenames',
        metavar='scriptname',
        nargs='+',
        help="Name of scriptfiles to be processed or exactly one .spec file. If a .spec file is specified, most "
        "options are unnecessary and are ignored.",
    )

    return parser


def run(pyi_args: list | None = None, pyi_config: dict | None = None):
    """
    pyi_args     allows running PyInstaller programmatically without a subprocess
    pyi_config   allows checking configuration once when running multiple tests
    """
    compat.check_requirements()
    check_unsafe_privileges()

    import PyInstaller.log

    old_sys_argv = sys.argv
    try:
        parser = generate_parser()
        autocomplete(parser)
        if pyi_args is None:
            pyi_args = sys.argv[1:]
        try:
            index = pyi_args.index("--")
        except ValueError:
            index = len(pyi_args)
        args = parser.parse_args(pyi_args[:index])
        spec_args = pyi_args[index + 1:]
        PyInstaller.log.__process_options(parser, args)

        # Print PyInstaller version, Python version, and platform as the first line to stdout. This helps us identify
        # PyInstaller, Python, and platform version when users report issues.
        try:
            from _pyinstaller_hooks_contrib import __version__ as contrib_hooks_version
        except Exception:
            contrib_hooks_version = 'unknown'

        logger.info('PyInstaller: %s, contrib hooks: %s', __version__, contrib_hooks_version)
        logger.info('Python: %s%s', platform.python_version(), " (conda)" if compat.is_conda else "")
        logger.info('Platform: %s', platform.platform())
        logger.info('Python environment: %s', sys.prefix)

        # Skip creating .spec when .spec file is supplied.
        if args.filenames[0].endswith('.spec'):
            parser._forbid_options(
                args, group="makespec", errmsg="makespec options not valid when a .spec file is given"
            )
            spec_file = args.filenames[0]
        else:
            # Ensure that the given script files exist, before trying to generate the .spec file.
            # This prevents us from overwriting an existing (and customized) .spec file if user makes a typo in the
            # .spec file's suffix when trying to  build it, for example, `pyinstaller program.cpes` (see #8276).
            # It also prevents creation of a .spec file when `pyinstaller program.py` is accidentally ran from a
            # directory that does not contain the script (for example, due to failing to change the directory prior
            # to running the command).
            for filename in args.filenames:
                if not os.path.isfile(filename):
                    raise SystemExit(f"Script file {filename!r} does not exist.")
            spec_file = run_makespec(**vars(args))

        sys.argv = [spec_file, *spec_args]
        run_build(pyi_config, spec_file, **vars(args))

    except KeyboardInterrupt:
        raise SystemExit("Aborted by user request.")
    except RecursionError:
        from PyInstaller import _recursion_too_deep_message
        _recursion_too_deep_message.raise_with_msg()
    finally:
        sys.argv = old_sys_argv


def _console_script_run():
    # Python prepends the main script's parent directory to sys.path. When PyInstaller is ran via the usual
    # `pyinstaller` CLI entry point, this directory is $pythonprefix/bin which should not be in sys.path.
    if os.path.basename(sys.path[0]) in ("bin", "Scripts"):
        sys.path.pop(0)
    run()


def check_unsafe_privileges():
    """
    Forbid dangerous usage of PyInstaller with escalated privileges
    """
    if compat.is_win and not compat.is_win_wine:
        # Discourage (with the intention to eventually block) people using *run as admin* with PyInstaller.
        # There are 4 cases, block case 3 but be careful not to also block case 2.
        #   1. User has no admin access: TokenElevationTypeDefault
        #   2. User is an admin/UAC disabled (common on CI/VMs): TokenElevationTypeDefault
        #   3. User has used *run as administrator* to elevate: TokenElevationTypeFull
        #   4. User can escalate but hasn't: TokenElevationTypeLimited
        # https://techcommunity.microsoft.com/t5/windows-blog-archive/how-to-determine-if-a-user-is-a-member-of-the-administrators/ba-p/228476
        import ctypes

        advapi32 = ctypes.CDLL("Advapi32.dll")
        kernel32 = ctypes.CDLL("kernel32.dll")

        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        process = kernel32.GetCurrentProcess()

        token = ctypes.c_void_p()
        try:
            TOKEN_QUERY = 8
            assert advapi32.OpenProcessToken(ctypes.c_void_p(process), TOKEN_QUERY, ctypes.byref(token))

            elevation_type = ctypes.c_int()
            TokenElevationType = 18
            assert advapi32.GetTokenInformation(
                token, TokenElevationType, ctypes.byref(elevation_type), ctypes.sizeof(elevation_type),
                ctypes.byref(ctypes.c_int())
            )
        finally:
            kernel32.CloseHandle(token)

        if elevation_type.value == 2:  # TokenElevationTypeFull
            logger.log(
                logging.DEPRECATION,
                "Running PyInstaller as admin is not necessary nor sensible. Run PyInstaller from a non-administrator "
                "terminal. PyInstaller 7.0 will block this."
            )

    elif compat.is_darwin or compat.is_linux:
        # Discourage (with the intention to eventually block) people using *sudo* with PyInstaller.
        # Again there are 4 cases, block only case 4.
        #   1. Non-root: os.getuid() != 0
        #   2. Logged in as root (usually a VM): os.getlogin() == "root", os.getuid() == 0
        #   3. No named users (e.g. most Docker containers): os.getlogin() fails
        #   4. Regular user using escalation: os.getlogin() != "root", os.getuid() == 0
        try:
            user = os.getlogin()
        except OSError:
            user = ""
        if os.getuid() == 0 and user and user != "root":
            logger.log(
                logging.DEPRECATION,
                "Running PyInstaller as root is not necessary nor sensible. Do not use PyInstaller with sudo. "
                "PyInstaller 7.0 will block this."
            )

    if compat.is_win:
        # Do not let people run PyInstaller from admin cmd's default working directory (C:\Windows\system32)
        cwd = pathlib.Path.cwd()

        try:
            win_dir = compat.win32api.GetWindowsDirectory()
        except Exception:
            win_dir = None
        win_dir = None if win_dir is None else pathlib.Path(win_dir).resolve()

        inside_win_dir = cwd == win_dir or win_dir in cwd.parents

        # The only exception to the above is if user's home directory is also located under %WINDIR%, which happens
        # when PyInstaller is ran under SYSTEM user.
        if inside_win_dir:
            home_dir = pathlib.Path.home().resolve()
            if cwd == home_dir or home_dir in cwd.parents:
                inside_win_dir = False

        if inside_win_dir:
            raise SystemExit(
                f"Error: Do not run pyinstaller from {cwd}. cd to where your code is and run pyinstaller from there. "
                "Hint: You can open a terminal where your code is by going to the parent folder in Windows file "
                "explorer and typing cmd into the address bar."
            )


if __name__ == '__main__':
    run()
