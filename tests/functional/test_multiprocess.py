# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
# ----------------------------------------------------------------------------

# Library imports
# ---------------
import os
import sys

# Local imports
# -------------
from PyInstaller.compat import is_py3, is_win
from PyInstaller.utils.tests import importorskip, skipif


@importorskip('multiprocessing')
def test_multiprocess(pyi_builder):
    pyi_builder.test_script('pyi_multiprocess.py')


@importorskip('multiprocessing')
def test_multiprocess_forking(pyi_builder):
    pyi_builder.test_script('pyi_multiprocess_forking.py')


@importorskip('multiprocessing')
def test_multiprocess_pool(pyi_builder):
    pyi_builder.test_script('pyi_multiprocess_pool.py')


@skipif(not is_py3, reason='set_start_method introduced in python 3.4+')
@importorskip('multiprocessing')
def test_multiprocess_spawn_semaphore(pyi_builder, capfd):
    pyi_builder.test_source("""
        import sys

        from multiprocessing import set_start_method, Process, Semaphore
        from multiprocessing import freeze_support
        from multiprocessing.util import log_to_stderr

        def test(s):
            s.acquire()
            print('In subprocess')
            s.release()

        if __name__ == '__main__':
            log_to_stderr()
            freeze_support()
            set_start_method('spawn')

            print('In main')
            sys.stdout.flush()
            s = Semaphore()
            s.acquire()
            proc = Process(target=test, args = [s])
            proc.start()
            s.release()
            proc.join()
        """)

    out, err = capfd.readouterr()

    # Print the captured output and error so that it will show up in the test output.
    sys.stderr.write(err)
    sys.stdout.write(out)

    expected = ["In main", "In subprocess"]

    assert os.linesep.join(expected) in out
    for substring in expected:
        assert out.count(substring) == 1


@skipif(not is_py3, reason='set_start_method introduced in python 3.4+')
@skipif(is_win, reason='fork is not available on windows')
@importorskip('multiprocessing')
def test_multiprocess_fork_semaphore(pyi_builder, capfd):
    pyi_builder.test_source("""
        import sys

        from multiprocessing import set_start_method, Process, Semaphore
        from multiprocessing import freeze_support
        from multiprocessing.util import log_to_stderr

        def test(s):
            s.acquire()
            print('In subprocess')
            s.release()

        if __name__ == '__main__':
            log_to_stderr()
            freeze_support()
            set_start_method('fork')

            print('In main')
            sys.stdout.flush()
            s = Semaphore()
            s.acquire()
            proc = Process(target=test, args = [s])
            proc.start()
            s.release()
            proc.join()
        """)

    out, err = capfd.readouterr()

    # Print the captured output and error so that it will show up in the test output.
    sys.stderr.write(err)
    sys.stdout.write(out)

    expected = ["In main", "In subprocess"]

    assert os.linesep.join(expected) in out
    for substring in expected:
        assert out.count(substring) == 1




@skipif(not is_py3, reason='set_start_method introduced in python 3.4+')
@skipif(is_win, reason='forkserver is not available on windows')
@importorskip('multiprocessing')
def test_multiprocess_forkserver_semaphore(pyi_builder, capfd):
    pyi_builder.test_source("""
        import sys

        from multiprocessing import set_start_method, Process, Semaphore
        from multiprocessing import freeze_support
        from multiprocessing.util import log_to_stderr

        def test(s):
            s.acquire()
            print('In subprocess')
            s.release()

        if __name__ == '__main__':
            log_to_stderr()
            freeze_support()
            set_start_method('forkserver')

            print('In main')
            sys.stdout.flush()
            s = Semaphore()
            s.acquire()
            proc = Process(target=test, args = [s])
            proc.start()
            s.release()
            proc.join()
        """)

    out, err = capfd.readouterr()

    # Print the captured output and error so that it will show up in the test output.
    sys.stderr.write(err)
    sys.stdout.write(out)

    expected = ["In main", "In subprocess"]

    assert os.linesep.join(expected) in out
    for substring in expected:
        assert out.count(substring) == 1






