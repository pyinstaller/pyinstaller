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


class SendEventProcess(multiprocessing.Process):
    def __init__(self, queue):
        multiprocessing.Process.__init__(self)
        self.queue = queue

    def run(self):
        print('SendEventProcess: begin')
        self.queue.put((1, 2))
        print('SendEventProcess: end')


def main(start_method):
    # Set start method
    multiprocessing.set_start_method(start_method)

    # Create a queue, and run a subprocess that fills it with data
    print('Main: begin')
    queue = multiprocessing.Queue()
    process = SendEventProcess(queue)
    process.start()

    results = queue.get()
    print(f'Main: retrieved results: {results}')
    assert results == (1, 2)

    process.join()
    print('Main: end')

    # Ensure process finished successfully
    assert process.exitcode == 0, f"Process exited with non-success code {process.exitcode}!"


if __name__ == '__main__':
    multiprocessing.freeze_support()

    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <start-method>")
        sys.exit(1)

    main(sys.argv[1])
