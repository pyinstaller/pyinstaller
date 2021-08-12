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

from PyInstaller.depend.imphook import AdditionalFilesCache


def test_binaries_and_datas():
    datas = [('source', 'dest'), ('src', 'dst')]
    binaries = [('abc', 'def'), ('ghi', 'jkl')]
    modules = ['testmodule1', 'testmodule2']

    cache = AdditionalFilesCache()
    for modname in modules:
        cache.add(modname, binaries, datas)
        assert cache.datas(modname) == datas
        cache.add(modname, binaries, datas)
        # This should be extended. Therefore it should be binaries*2
        assert cache.binaries(modname) != binaries
        assert cache.binaries(modname) == binaries * 2
