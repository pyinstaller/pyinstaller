#-----------------------------------------------------------------------------
# Copyright (c) 2005-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import multiprocessing


class SendeventProcess(multiprocessing.Process):
    def __init__(self, resultQueue):
        multiprocessing.Process.__init__(self)
        self.resultQueue = resultQueue
        self.start()

    def run(self):
        print('SendeventProcess begins')
        self.resultQueue.put((1, 2))
        print('SendeventProcess ends')


if __name__ == '__main__':
    multiprocessing.freeze_support()
    print('main begins')
    resultQueue = multiprocessing.Queue()
    sp = SendeventProcess(resultQueue)
    assert resultQueue.get() == (1, 2)
    print('get ends')
    sp.join()
    print('main ends')
