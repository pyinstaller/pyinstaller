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
