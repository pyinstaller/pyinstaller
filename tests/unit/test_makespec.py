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

import os

from PyInstaller.building import makespec


def test_make_variable_path():
    p = os.path.join(makespec.HOMEPATH, "aaa", "bbb", "ccc")
    assert (makespec.make_variable_path(p) == ("HOMEPATH", os.path.join("aaa", "bbb", "ccc")))


def test_make_variable_path_regression():
    p = os.path.join(makespec.HOMEPATH + "aaa", "bbb", "ccc")
    assert makespec.make_variable_path(p) == (None, p)


def test_Path_constructor():
    p = makespec.Path("aaa", "bbb", "ccc")
    assert p.path == os.path.join("aaa", "bbb", "ccc")


def test_Path_repr():
    p = makespec.Path(makespec.HOMEPATH, "aaa", "bbb", "ccc")
    assert p.path == os.path.join(makespec.HOMEPATH, "aaa", "bbb", "ccc")
    assert (repr(p) == "os.path.join(HOMEPATH,%r)" % os.path.join("aaa", "bbb", "ccc"))


def test_Path_repr_relative():
    p = makespec.Path("aaa", "bbb", "ccc.py")
    assert p.path == os.path.join("aaa", "bbb", "ccc.py")
    assert repr(p) == "%r" % os.path.join("aaa", "bbb", "ccc.py")


def test_Path_regression():
    p = makespec.Path(makespec.HOMEPATH + "-aaa", "bbb", "ccc")
    assert p.path == os.path.join(makespec.HOMEPATH + "-aaa", "bbb", "ccc")
    assert (repr(p) == repr(os.path.join(makespec.HOMEPATH + "-aaa", "bbb", "ccc")))
