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


def f(x):
    return x * x


def main(start_method):
    multiprocessing.set_start_method(start_method)

    # Start a pool with 4 worker processes.
    with multiprocessing.Pool(processes=4) as pool:
        print('Evaluate f(10) asynchronously...')
        result = pool.apply_async(f, [10])
        assert result.get() == 100

        print('Evaluate f(0..9)...')
        assert pool.map(f, range(10)) == [x**2 for x in range(10)]


if __name__ == '__main__':
    multiprocessing.freeze_support()

    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <start-method>")
        sys.exit(1)

    main(sys.argv[1])
