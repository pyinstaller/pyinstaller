#-----------------------------------------------------------------------------
# Copyright (c) 2013-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import sys
import multiprocessing


class SendeventProcess(multiprocessing.Process):
    def __init__(self, resultQueue):
        self.resultQueue = resultQueue

        multiprocessing.Process.__init__(self)
        self.start()

    def run(self):
        print('SendeventProcess')
        self.resultQueue.put((1, 2))
        print('SendeventProcess')


if __name__ == '__main__':
    multiprocessing.freeze_support()
    print('main')
    resultQueue = multiprocessing.Queue()
    SendeventProcess(resultQueue)
    print('main')
