#-----------------------------------------------------------------------------
# Copyright (c) 2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

# Test that we can start a nested `multiprocessing.Process` from within a `multiprocessing.Process`. See #7494.

import sys
import multiprocessing


def nested_process_function(queue):
    print("Running nested sub-process!")
    queue.put(2)


def process_function(queue):
    print("Running sub-process!")
    queue.put(1)

    process = multiprocessing.Process(target=nested_process_function, args=(queue,))
    process.start()
    process.join()


def main(start_method):
    multiprocessing.set_start_method(start_method)
    queue = multiprocessing.Queue()

    process = multiprocessing.Process(target=process_function, args=(queue,))
    process.start()
    process.join()

    # Read results from queue; we expect one for each process.
    # NOTE: this goes against the `multiprocessing` programming recommendations, because we should read from queue
    # before joining the feeding processes, lest we incur a deadlock when queue's buffer fills up. However, as we put in
    # only two  elements, we take a calculated risk; this way, we can read only available items post-hoc, which in turn
    # allows us to avoid blocking forever if a process happens to fail for some reason.
    results = []
    while not queue.empty():
        results.append(queue.get())

    # NOTE: as per [1]: "If multiple processes are enqueuing objects, it is possible for the objects to be received at
    # the other end out-of-order. However, objects enqueued by the same process will always be in the expected order
    # with respect to each other."
    # [1] https://docs.python.org/3/library/multiprocessing.html#pipes-and-queues
    #
    # Therefore, accept either order of results as a valid one.
    print(f"Results: {results}")
    assert results == [1, 2] or results == [2, 1]


if __name__ == '__main__':
    multiprocessing.freeze_support()

    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <start-method>")
        sys.exit(1)

    main(sys.argv[1])
