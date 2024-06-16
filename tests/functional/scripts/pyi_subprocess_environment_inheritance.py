#-----------------------------------------------------------------------------
# Copyright (c) 2024, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import argparse
import os
import sys
import subprocess

if __name__ == '__main__':
    # Argument parser
    parser = argparse.ArgumentParser(description="Sub-process environment inheritance test")
    subparsers = parser.add_subparsers(dest="process_type", help="Process type.")

    parser_parent = subparsers.add_parser("parent", help="Parent process.")
    parser_parent.add_argument(
        "child_executable",
        type=str,
        help="Path to executable to spawn as a child process.",
    )
    parser_parent.add_argument(
        "--force-independent",
        action="store_true",
        help="Spawn the child process as an independent instance.",
    )

    parser_child = subparsers.add_parser("child", help="Child process.")
    parser_child.add_argument(
        "mode",
        type=str,
        choices={"same", "different"},
        help="Child mode - whether executable is the same as parent process or not.",
    )
    parser_child.add_argument(
        "parent_app_dir",
        type=str,
        help="Top-level application directory of the parent process.",
    )

    args = parser.parse_args()

    if args.process_type is None:
        # Process type not specified - exit early.
        print("Process type not specified.", file=sys.stderr)
    elif args.process_type == "parent":
        # Parent process.
        print("Running as parent process!", file=sys.stderr)
        print(f"Child executable: {args.child_executable}", file=sys.stderr)
        print(f"Force independent instance: {args.force_independent}", file=sys.stderr)

        env = os.environ.copy()

        if (
            args.child_executable == "sys.executable"
            or os.path.realpath(args.child_executable) == os.path.realpath(sys.executable)
        ):
            subprocess_args = [
                sys.executable,
                "child",
                "different" if args.force_independent else "same",
                sys._MEIPASS,
            ]

            if args.force_independent:
                env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
        else:
            subprocess_args = [
                args.child_executable,
                "child",
                "different",
                sys._MEIPASS,
            ]

        print(f"Running child process with arguments: {subprocess_args!r}", file=sys.stderr)
        subprocess.run(subprocess_args, check=True, env=env)
    else:
        # Child process.
        print("Running as child process!", file=sys.stderr)
        print(f"Mode: {args.mode}", file=sys.stderr)
        print(f"Our top-level directory: {sys._MEIPASS}", file=sys.stderr)
        print(f"Parent top-level directory: {args.parent_app_dir}", file=sys.stderr)

        if args.mode == "same":
            # Raise error if directories are different.
            if sys._MEIPASS != args.parent_app_dir:
                raise SystemExit(
                    f"Expected top-level directory ({sys._MEIPASS}) to be SAME as that of the parent process "
                    f"({args.parent_app_dir}), but it is not!"
                )
        else:
            # Raise error if directories are the same.
            if sys._MEIPASS == args.parent_app_dir:
                raise SystemExit(
                    f"Expected top-level directory ({sys._MEIPASS}) to be DIFFERENT from that of the parent process "
                    f"({args.parent_app_dir}), but it is not!"
                )
