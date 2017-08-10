# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2005-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import sys
import pytest

from PyInstaller.utils.tests import skipif_notosx, xfail_py2


def test_ctypes_cdll_unknown_dll(pyi_builder, capfd):
    with pytest.raises(AssertionError):
        pyi_builder.test_source("""
            import ctypes
            ctypes.cdll.LoadLibrary('non-existing-2017')
            """)
    out, err = capfd.readouterr()
    assert "Failed to load dynlib/dll" in err


@skipif_notosx
@xfail_py2
def test_issue_2322(pyi_builder, capfd):
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

    assert "\n".join(expected) in out
    for substring in expected:
        assert out.count(substring) == 1
