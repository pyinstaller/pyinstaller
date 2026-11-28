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

import os

import pytest

from PyInstaller import compat
from PyInstaller._shared_with_waf import _pyi_machine


def test_exec_command_subprocess_wrong_encoding_reports_nicely(capsys):
    # Ensure a nice error message is printed if decoding the output of the subprocess fails.
    # As `exec_python()` is used for running the program, we can use a small Python script.
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
        ("sunway", "sunway"),
        ("sw_64", "sunway"),
        ("loongarch", "loongarch"),
        ("loongarch64", "loongarch"),
        ("something-alien", "unknown"),
    ]
)
def test_linux_machine(input, output):
    assert _pyi_machine(input, "Linux") == output


def test_windows_machine():
    assert _pyi_machine("AMD64", "Windows") == "intel"
    assert _pyi_machine("ARM64", "Windows") == "arm"


def test_other_os_machine():
    assert _pyi_machine("foo", "Darwin") is None
    assert _pyi_machine("foo", "FreeBSD") is None


def test_exec_python_forces_utf8_io_encoding(monkeypatch):
    # `exec_python()` always decodes the captured output as utf-8, so it must also force the child process to write its
    # output as utf-8 - including when the child would otherwise inherit a different `PYTHONIOENCODING` from us.
    monkeypatch.setenv("PYTHONIOENCODING", "latin-1")

    prog = "print('\\u00f8')"

    # Environment passed explicitly.
    assert compat.exec_python('-c', prog, env=dict(os.environ)).strip() == '\u00f8'

    # Environment not passed, so that it is constructed from `os.environ`.
    assert compat.exec_python('-c', prog).strip() == '\u00f8'


def test_exec_python_does_not_modify_passed_environment():
    # Forcing `PYTHONIOENCODING` must not be done by modifying the caller's mapping in place.
    env = dict(os.environ)
    compat.exec_python('-c', 'pass', env=env)
    assert env == os.environ
