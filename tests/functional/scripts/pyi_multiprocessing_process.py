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
import time
import multiprocessing


def test_function():
    time.sleep(1)
    print('In subprocess')


def main(start_method):
    # Set start method
    multiprocessing.set_start_method(start_method)

    # Start a sub-process
    print('In main')
    process = multiprocessing.Process(target=test_function)
    process.start()
    process.join()

    # Ensure process finished successfully
    assert process.exitcode == 0, f"Process exited with non-success code {process.exitcode}!"


if __name__ == '__main__':
    multiprocessing.freeze_support()

    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <start-method>")
        sys.exit(1)

    main(sys.argv[1])
