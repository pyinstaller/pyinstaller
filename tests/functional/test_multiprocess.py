# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright (c) 2005-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
# ----------------------------------------------------------------------------

import os
import sys
import pytest

from PyInstaller.compat import is_win
from PyInstaller.utils.tests import importorskip, skipif


@importorskip('multiprocessing')
@pytest.mark.timeout(timeout=60)
def test_multiprocess(pyi_builder):
    pyi_builder.test_script('pyi_multiprocess.py')


@importorskip('multiprocessing')
@pytest.mark.timeout(timeout=60)
def test_multiprocess_forking(pyi_builder):
    pyi_builder.test_script('pyi_multiprocess_forking.py')


@importorskip('multiprocessing')
@pytest.mark.timeout(timeout=60)
def test_multiprocess_pool(pyi_builder):
    pyi_builder.test_script('pyi_multiprocess_pool.py')


@importorskip('multiprocessing')
@pytest.mark.timeout(timeout=60)
def test_multiprocess_spawn_semaphore(pyi_builder, capfd):
    pyi_builder.test_source(
        """
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
        """
    )

    out, err = capfd.readouterr()

    # Print the captured output and error so that it will show up in the test output.
    sys.stderr.write(err)
    sys.stdout.write(out)

    expected = ["In main", "In subprocess"]

    assert os.linesep.join(expected) in out
    for substring in expected:
        assert out.count(substring) == 1


@skipif(is_win, reason='fork is not available on windows')
@importorskip('multiprocessing')
@pytest.mark.timeout(timeout=60)
def test_multiprocess_fork_semaphore(pyi_builder, capfd):
    pyi_builder.test_source(
        """
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
        """
    )

    out, err = capfd.readouterr()

    # Print the captured output and error so that it will show up in the test output.
    sys.stderr.write(err)
    sys.stdout.write(out)

    expected = ["In main", "In subprocess"]

    assert os.linesep.join(expected) in out
    for substring in expected:
        assert out.count(substring) == 1


@skipif(is_win, reason='forkserver is not available on windows')
@importorskip('multiprocessing')
@pytest.mark.timeout(timeout=60)
def test_multiprocess_forkserver_semaphore(pyi_builder, capfd):
    pyi_builder.test_source(
        """
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
        """
    )

    out, err = capfd.readouterr()

    # Print the captured output and error so that it will show up in the test output.
    sys.stderr.write(err)
    sys.stdout.write(out)

    expected = ["In main", "In subprocess"]

    assert os.linesep.join(expected) in out
    for substring in expected:
        assert out.count(substring) == 1


@importorskip('multiprocessing')
@pytest.mark.timeout(timeout=60)
def test_multiprocess_spawn_process(pyi_builder, capfd):
    # Test whether this terminates, see issue #4865
    pyi_builder.test_source(
        """
        import sys, time
        import multiprocessing as mp

        def test():
            time.sleep(1)
            print('In subprocess')

        print(sys.argv)
        mp.freeze_support()
        mp.set_start_method('spawn')

        print('In main')
        proc = mp.Process(target=test)
        proc.start()
        proc.join()
        """
    )


@importorskip('multiprocessing')
@pytest.mark.timeout(timeout=60)
def test_multiprocess_spawn_pool(pyi_builder, capfd):
    # Test whether this terminates, see issue #4865
    pyi_builder.test_source(
        """
        import sys, time
        import multiprocessing as mp

        def test(s):
            time.sleep(1)
            print(s)

        print(sys.argv,)
        mp.freeze_support()
        mp.set_start_method('spawn')

        print('In main')
        with mp.Pool() as p:
            p.map(test, 'in pool')
        """
    )
