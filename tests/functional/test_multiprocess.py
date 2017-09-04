# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright (c) 2005-2017, PyInstaller Development Team.
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
from PyInstaller.compat import is_py34
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


@skipif(not is_py34, reason='Spawn was introduced in python 3.4+')
@importorskip('multiprocessing')
def test_multiprocess_spawn(pyi_builder, capfd):
    pyi_builder.test_source("""
        from multiprocessing import set_start_method, Process
        from multiprocessing import freeze_support
        from multiprocessing.util import log_to_stderr

        def test():
            print('In subprocess')

        if __name__ == '__main__':
            log_to_stderr()
            freeze_support()
            set_start_method('spawn')

            print('In main')
            proc = Process(target=test)
            proc.start()
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

