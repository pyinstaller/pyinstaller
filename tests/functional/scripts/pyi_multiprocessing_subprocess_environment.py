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

import sys
import multiprocessing


def get_sys_meipass():
    return str(sys._MEIPASS)


def main(start_method):
    multiprocessing.set_start_method(start_method)

    # Start a pool with 4 worker processes.
    print('Running subprocess(es)...')
    with multiprocessing.Pool(processes=4) as pool:
        result = pool.apply_async(get_sys_meipass)
        subprocess_meipass = result.get()

        print(f"sys._MEIPASS in main process: {sys._MEIPASS}")
        print(f"sys._MEIPASS in sub-process: {subprocess_meipass}")

        assert sys._MEIPASS == subprocess_meipass


if __name__ == '__main__':
    multiprocessing.freeze_support()

    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <start-method>")
        sys.exit(1)

    main(sys.argv[1])
