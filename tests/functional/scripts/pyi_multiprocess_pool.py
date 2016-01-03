#-----------------------------------------------------------------------------
# Copyright (c) 2013-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Bootloader unsets _MEIPASS2 for child processes to allow running
# PyInstaller binaries inside pyinstaller binaries.
# This is ok for mac or unix with fork() system call.
# But on Windows we need to overcome missing fork() fuction.
#
# See http://www.pyinstaller.org/wiki/Recipe/Multiprocessing

import os
import sys

# Module multiprocessing is organized differently in Python 3.4+
try:
    # Python 3.4+
    if sys.platform.startswith('win'):
        import multiprocessing.popen_spawn_win32 as forking
    else:
        import multiprocessing.popen_fork as forking
except ImportError:
    import multiprocessing.forking as forking


if sys.platform.startswith('win'):
    # First define a modified version of Popen.
    class _Popen(forking.Popen):
        def __init__(self, *args, **kw):
            if hasattr(sys, 'frozen'):
                # We have to set original _MEIPASS2 value from sys._MEIPASS
                # to get --onefile mode working.
                os.putenv('_MEIPASS2', sys._MEIPASS)
            try:
                super(_Popen, self).__init__(*args, **kw)
            finally:
                if hasattr(sys, 'frozen'):
                    # On some platforms (e.g. AIX) 'os.unsetenv()' is not
                    # available. In those cases we cannot delete the variable
                    # but only set it to the empty string. The bootloader
                    # can handle this case.
                    if hasattr(os, 'unsetenv'):
                        os.unsetenv('_MEIPASS2')
                    else:
                        os.putenv('_MEIPASS2', '')

    # Second override 'Popen' class with our modified version.
    forking.Popen = _Popen


import multiprocessing


def  f(x):
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
