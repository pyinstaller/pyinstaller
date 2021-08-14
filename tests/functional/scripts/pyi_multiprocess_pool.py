#-----------------------------------------------------------------------------
# Copyright (c) 2013-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import multiprocessing


def f(x):
    return x * x


if __name__ == '__main__':
    multiprocessing.freeze_support()
    # Start 4 worker processes.
    pool = multiprocessing.Pool(processes=4)
    print('Evaluate "f(10)" asynchronously.')
    res = pool.apply_async(f, [10])
    print(res.get(timeout=1))  # prints "100"
    print('Print "[0, 1, 4,..., 81]"')
    print(pool.map(f, range(10)))
    # This is old code, based on Python 2, and does not use Pool as a context, so we need to
    # explicitly terminate the pool.
    pool.terminate()
