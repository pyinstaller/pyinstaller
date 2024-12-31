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
import multiprocessing


def test_function(semaphore):
    semaphore.acquire()
    print('In subprocess')
    semaphore.release()


def main(start_method):
    multiprocessing.set_start_method(start_method)

    print('In main')
    sys.stdout.flush()
    semaphore = multiprocessing.Semaphore()
    semaphore.acquire()
    process = multiprocessing.Process(target=test_function, args=[semaphore])
    process.start()
    semaphore.release()
    process.join()


if __name__ == '__main__':
    multiprocessing.freeze_support()

    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <start-method>")
        sys.exit(1)

    main(sys.argv[1])
