#-----------------------------------------------------------------------------
# Copyright (c) 2013-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import multiprocessing


def f(x):
    return x*x


if __name__ == '__main__':
    multiprocessing.freeze_support()
    # Start 4 worker processes.
    pool = multiprocessing.Pool(processes=4)
    print('Evaluate "f(10)" asynchronously.')
    res = pool.apply_async(f, [10])
    print(res.get(timeout=1))          # prints "100"
    print('Print "[0, 1, 4,..., 81]"')
    print(pool.map(f, range(10)))
