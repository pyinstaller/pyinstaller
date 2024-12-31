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

# Test that we can start `multiprocessing.Process` in thread-safe manner concurrently, from multiple threads at (almost)
# the same time. See #7410.

import sys
import threading
import multiprocessing

NUM_THREADS = 4


def process_function(queue, i):
    print(f"Running process function with i={i}")
    queue.put(i)


def thread_function(queue, i):
    process = multiprocessing.Process(target=process_function, args=(queue, i))
    process.start()
    process.join()

    assert process.exitcode == 0, f"Process {i} exited with non-succcess code {process.exitcode}!"


def main(start_method):
    multiprocessing.set_start_method(start_method)
    queue = multiprocessing.Queue()

    threads = []
    for i in range(NUM_THREADS):
        threads.append(threading.Thread(target=thread_function, args=(queue, i), daemon=True))

    # Start threads
    for thread in threads:
        thread.start()

    # Wait for threads to finish
    for thread in threads:
        thread.join()

    # Read results from queue; we expect one for each thread.
    # NOTE: this goes against the `multiprocessing` programming recommendations, because we should read from queue
    # before joining the feeding processes (and thus, their spawning threads), lest we incur a deadlock when queue's
    # buffer fills up. However, as we put in only four elements, we take a calculated risk; this way, we can read only
    # available items post-hoc, which in turn allows us to avoid blocking forever if a process happens to fail for some
    # reason.
    results = []
    while not queue.empty():
        results.append(queue.get())

    print(f"Results: {results}")
    assert sorted(results) == list(range(NUM_THREADS))


if __name__ == '__main__':
    multiprocessing.freeze_support()

    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <start-method>")
        sys.exit(1)

    main(sys.argv[1])
