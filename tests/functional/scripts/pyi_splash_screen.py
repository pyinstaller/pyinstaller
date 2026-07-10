# -----------------------------------------------------------------------------
# Copyright (c) 2019-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
# -----------------------------------------------------------------------------

# This script establishes a simple communication with the bootloader to test the functions.

import sys
import time


def main():
    # Init pyi_splash / connect to the bootloader.
    print("Importing pyi_splash...", file=sys.stderr)
    import pyi_splash

    # Simulate users program startup.
    time.sleep(1)
    print("Updating text...", file=sys.stderr)
    pyi_splash.update_text("This is a test text")
    time.sleep(2)
    print("Updating text again...", file=sys.stderr)
    pyi_splash.update_text("Second time's a charm")

    # Close the splash screen to check if that works.
    time.sleep(1)
    print("Closing splash screen...", file=sys.stderr)
    pyi_splash.close()

    # Exit
    time.sleep(1)
    print("End of program reached!", file=sys.stderr)


if __name__ == '__main__':
    main()
