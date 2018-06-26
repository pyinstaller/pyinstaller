#-----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from PyInstaller.compat import is_py2
from PyInstaller.utils.tests import skipif

import pytest

from PyInstaller import compat


@skipif(is_py2, reason="In Python 2, subprocess' stdout is not decoded")
def test_exec_command_subprocess_wrong_encoding_reports_nicely(capsys):
    # Ensure a nice error message is printed if decoding the output of the
    # subprocess fails.
    # Actually `exec_python()` is used for running the progam, so we can use a
    # small Python script.
    prog = ("""import sys; sys.stdout.buffer.write(b'dfadfadf\\xa0:::::')""")
    with pytest.raises(UnicodeDecodeError):
        res = compat.exec_python('-c', prog)
    out, err = capsys.readouterr()
    assert 'bytes around the offending' in err
