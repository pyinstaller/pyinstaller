#-----------------------------------------------------------------------------
# Copyright (c) 2015-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

from PyInstaller.utils.hooks import collect_all, copy_metadata
from PyInstaller.compat import is_win

excludedimports = ["gevent.testing", "gevent.tests"]

datas, binaries, hiddenimports = collect_all(
    'gevent',
    filter_submodules=lambda name: (
        "gevent.testing" not in name or "gevent.tests" not in name),
    include_py_files=False,
    exclude_datas=["**/tests"])

datas += copy_metadata("zope.interface")
datas += copy_metadata("greenlet")
datas += copy_metadata("zope.event")
datas += copy_metadata("setuptools")

if is_win:
    datas += copy_metadata("cffi")
    datas += copy_metadata("pycparser")
