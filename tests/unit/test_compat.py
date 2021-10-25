#-----------------------------------------------------------------------------
# Copyright (c) 2005-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import pytest

from PyInstaller import compat
from PyInstaller._shared_with_waf import _pyi_machine


def test_exec_command_subprocess_wrong_encoding_reports_nicely(capsys):
    # Ensure a nice error message is printed if decoding the output of the subprocess fails.
    # As `exec_python()` is used for running the progam, we can use a small Python script.
    prog = """import sys; sys.stdout.buffer.write(b'dfadfadf\\xa0:::::')"""
    with pytest.raises(UnicodeDecodeError):
        compat.exec_python('-c', prog)
    out, err = capsys.readouterr()
    assert 'bytes around the offending' in err


# List every known platform.machine() or waf's ctx.env.DEST_CPU (in the bootloader/wscript file) output on Linux here.
@pytest.mark.parametrize(
    "input, output", [
        ("x86_64", "intel"),
        ("x64", "intel"),
        ("i686", "intel"),
        ("i386", "intel"),
        ("x86", "intel"),
        ("armv5", "arm"),
        ("armv7h", "arm"),
        ("armv7a", "arm"),
        ("arm", "arm"),
        ("aarch64", "arm"),
        ("ppc64le", "ppc"),
        ("ppc64", "ppc"),
        ("ppc32le", "ppc"),
        ("powerpc", "ppc"),
        ("s390x", "s390x"),
        ("mips", "mips"),
        ("mips64", "mips"),
        ("something-alien", "unknown"),
    ]
)
def test_linux_machine(input, output):
    assert _pyi_machine(input, "Linux") == output


def test_non_linux_machine():
    assert _pyi_machine("foo", "Darwin") is None
    assert _pyi_machine("foo", "Windows") is None
    assert _pyi_machine("foo", "FreeBSD") is None
