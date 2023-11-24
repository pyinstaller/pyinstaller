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
import argparse

import pytest

from PyInstaller.building import makespec


def test_add_data(capsys):
    """
    Test CLI parsing of --add-data and --add-binary.
    """
    parser = argparse.ArgumentParser()
    makespec.__add_options(parser)

    assert parser.parse_args([]).datas == []
    assert parser.parse_args(["--add-data", "/foo/bar:."]).datas == [("/foo/bar", ".")]
    if os.name == "nt":
        assert parser.parse_args([r"--add-data=C:\foo\bar:baz"]).datas == [(r"C:/foo/bar", "baz")]
    assert parser.parse_args([r"--add-data=c:/foo/bar:baz"]).datas == [(r"c:/foo/bar", "baz")]
    assert parser.parse_args([r"--add-data=/foo/:bar"]).datas == [("/foo", "bar")]

    for args in [["--add-data", "foo/bar"], ["--add-data", "C:/foo/bar"]]:
        with pytest.raises(SystemExit):
            parser.parse_args(args)
        assert '--add-data: Wrong syntax, should be --add-data=SOURCE:DEST' in capsys.readouterr().err

    if os.pathsep == ";":
        assert parser.parse_args(["--add-data", "foo;."]).datas == [("foo", ".")]
    else:
        assert parser.parse_args(["--add-data", "foo;bar:."]).datas == [("foo;bar", ".")]

    with pytest.raises(SystemExit):
        parser.parse_args(["--add-data", "foo:"])
    assert '--add-data: You have to specify both SOURCE and DEST' in capsys.readouterr().err

    options = parser.parse_args(["--add-data=a:b", "--add-data=c:d", "--add-binary=e:f"])
    assert options.datas == [("a", "b"), ("c", "d")]
    assert options.binaries == [("e", "f")]
