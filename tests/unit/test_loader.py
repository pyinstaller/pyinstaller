#-----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


from threading import Thread

from PyInstaller.compat import is_py2
from PyInstaller.loader.pyimod02_archive import ArchiveFile

if is_py2:
    from Queue import Queue
else:
    from queue import Queue


def test_threading_import(tmpdir):
    """
    On Python 3.3+, PyInstaller doesn't acquire a lock when performing an
    import. Therefore, two thread could both be reading the .pyz archive at the
    same time. At the core, the ArchiveFile class performs these reads. This
    test verifies that multi-threaded reads work.

    For more information, see https://github.com/pyinstaller/pyinstaller/pull/2010.
    """

    # Create a temporary file and use the ArchiveReader on it.
    tmp_file = tmpdir.join('test.txt')
    tmp_file.write('Testing')
    ar = ArchiveFile(tmp_file.strpath, 'r')

    # Use queues to synchronize threads.
    q1 = Queue()
    q2 = Queue()

    # This function, which is run in a separate thread, works to ensure that
    # both threads open a file at the same time.
    def foo():
        with ar:
            # Wait until both threads have opened the file.
            q1.put(1)
            assert q2.get() == 2
            # Wait until the other thread has closed the file before closing it
            # here.
            assert q2.get() == 3

    thread = Thread(target=foo)
    thread.start()

    # This code works with ``foo`` above to open the same file from two threads.
    with ar:
        # Wait until both threads have opened the file.
        q2.put(2)
        assert q1.get() == 1
    # Make the other thread wait until this thread has closed the file.
    q2.put(3)

    # Wait for the other thread to finish.
    thread.join()

