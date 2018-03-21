#-----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import multiprocessing
import sys


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
